{%- if cookiecutter.use_agentscope %}
"""Contract tests for tenant-scoped Mem0 User Memory."""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

import pytest

from app.services.agentscope_memory import (
    AgentScopeUserMemoryAdapter,
    MemoryBackendUnavailable,
    MemoryConsentRequired,
    MemoryNotFound,
    UserMemoryContext,
    UserMemoryScope,
)


class FakeMem0:
    """Small async Mem0 boundary fake that retains namespace arguments."""

    def __init__(self) -> None:
        self.records: dict[str, list[dict[str, Any]]] = {}
        self.search_calls: list[dict[str, Any]] = []
        self.add_calls: list[dict[str, Any]] = []
        self.delete_calls: list[dict[str, Any]] = []
        self.fail = False
        self._next_id = 0

    @staticmethod
    def _key(user_id: str, agent_id: str) -> str:
        return f"{user_id}|{agent_id}"

    async def search(self, query: str, **kwargs: Any) -> dict[str, Any]:
        if self.fail:
            raise RuntimeError("provider is unavailable")
        self.search_calls.append({"query": query, **kwargs})
        filters = kwargs["filters"]
        rows = self.records.get(self._key(filters["user_id"], filters["agent_id"]), [])
        return {"results": list(rows)[: kwargs.get("top_k", 5)]}

    async def add(self, messages: list[dict[str, str]], **kwargs: Any) -> dict[str, Any]:
        if self.fail:
            raise RuntimeError("provider is unavailable")
        self.add_calls.append({"messages": messages, **kwargs})
        self._next_id += 1
        row = {
            "id": f"memory-{self._next_id}",
            "memory": messages[0]["content"],
            "metadata": dict(kwargs.get("metadata") or {}),
        }
        key = self._key(kwargs["user_id"], kwargs["agent_id"])
        self.records.setdefault(key, []).append(row)
        return {"results": [row]}

    async def get_all(self, **kwargs: Any) -> dict[str, Any]:
        if self.fail:
            raise RuntimeError("provider is unavailable")
        filters = kwargs["filters"]
        return {"results": list(self.records.get(self._key(filters["user_id"], filters["agent_id"]), []))}

    async def delete(self, memory_id: str) -> None:
        if self.fail:
            raise RuntimeError("provider is unavailable")
        self.delete_calls.append({"memory_id": memory_id})
        for key, rows in self.records.items():
            self.records[key] = [row for row in rows if row.get("id") != memory_id]

    async def delete_all(self, **kwargs: Any) -> None:
        if self.fail:
            raise RuntimeError("provider is unavailable")
        self.delete_calls.append(kwargs)
        self.records.pop(self._key(kwargs["user_id"], kwargs["agent_id"]), None)


def _context(
    tenant_id: str = "tenant-a",
    user_id: str = "user-a",
    agent_definition_id: str = "agent-a",
    *,
    consent_granted: bool = True,
) -> UserMemoryContext:
    return UserMemoryContext(
        scope=UserMemoryScope(
            tenant_id=tenant_id,
            user_id=user_id,
            agent_definition_id=agent_definition_id,
        ),
        consent_granted=consent_granted,
    )


@pytest.mark.anyio
async def test_memory_namespace_isolated_by_tenant_user_and_agent() -> None:
    backend = FakeMem0()
    adapter = AgentScopeUserMemoryAdapter(backend)

    await adapter.remember(_context(), "Alice prefers concise answers")
    await adapter.remember(_context(tenant_id="tenant-b"), "Tenant B secret")
    await adapter.remember(_context(user_id="user-b"), "User B secret")
    await adapter.remember(_context(agent_definition_id="agent-b"), "Agent B secret")

    result = await adapter.search(_context(), "preferences")
    assert [item.text for item in result] == ["Alice prefers concise answers"]
    call = backend.search_calls[-1]
    assert call["filters"] == {
        "user_id": _context().scope.mem0_user_id,
        "agent_id": _context().scope.mem0_agent_id,
    }


@pytest.mark.anyio
async def test_memory_is_available_to_a_fresh_context_for_same_scope() -> None:
    backend = FakeMem0()
    first = AgentScopeUserMemoryAdapter(backend)
    second = AgentScopeUserMemoryAdapter(backend)

    await first.remember(_context(), "cross-session fact")
    result = await second.read(_context(), "fact")

    assert [item.text for item in result] == ["cross-session fact"]


@pytest.mark.anyio
async def test_memory_without_complete_namespace_metadata_is_rejected() -> None:
    backend = FakeMem0()
    scope = _context().scope
    backend.records[backend._key(scope.mem0_user_id, scope.mem0_agent_id)] = [
        {"id": "unscoped", "memory": "must not leak", "metadata": {"tenant_id": scope.tenant_id}}
    ]

    assert await AgentScopeUserMemoryAdapter(backend).search(_context(), "leak") == []


@pytest.mark.anyio
async def test_consent_is_required_for_runtime_read_write_and_middleware() -> None:
    adapter = AgentScopeUserMemoryAdapter(FakeMem0())
    context = _context(consent_granted=False)

    with pytest.raises(MemoryConsentRequired):
        await adapter.search(context, "anything")
    with pytest.raises(MemoryConsentRequired):
        await adapter.remember(context, "anything")
    with pytest.raises(MemoryConsentRequired):
        adapter.build_middleware(context)


@pytest.mark.anyio
async def test_build_middleware_uses_public_mem0_extension_seam() -> None:
    backend = FakeMem0()
    adapter = AgentScopeUserMemoryAdapter(backend)

    middleware = adapter.build_middleware(_context())
    tools = await middleware.list_tools()

    assert {tool.name for tool in tools} == {"search_memory", "add_memory"}
    await tools[1](thinking="durable fact", content=["written by AgentScope"])
    assert [item.text for item in await adapter.search(_context(), "AgentScope")] == [
        "written by AgentScope"
    ]


@pytest.mark.anyio
async def test_delete_checks_namespace_before_deleting_a_memory() -> None:
    backend = FakeMem0()
    adapter = AgentScopeUserMemoryAdapter(backend)
    created = await adapter.write(_context(), "delete me")

    await adapter.delete(_context(), created.memory_id or "")
    assert await adapter.search(_context(), "delete") == []
    with pytest.raises(MemoryNotFound):
        await adapter.delete(_context(), created.memory_id or "")

    other = await adapter.remember(_context(tenant_id="tenant-b"), "keep me")
    with pytest.raises(MemoryNotFound):
        await adapter.delete(_context(), other.memory_id or "")
    assert [item.text for item in await adapter.search(_context(tenant_id="tenant-b"), "keep")] == [
        "keep me"
    ]


@pytest.mark.anyio
async def test_delete_all_is_lifecycle_operation_and_does_not_require_consent() -> None:
    backend = FakeMem0()
    adapter = AgentScopeUserMemoryAdapter(backend)
    await adapter.remember(_context(), "private fact")

    await adapter.delete_all(_context(consent_granted=False).scope)

    assert await adapter.search(_context(), "private") == []
    assert backend.delete_calls[-1] == {
        "user_id": _context().scope.mem0_user_id,
        "agent_id": _context().scope.mem0_agent_id,
    }


@pytest.mark.anyio
async def test_retention_is_forwarded_and_expired_memory_is_rejected() -> None:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    backend = FakeMem0()
    adapter = AgentScopeUserMemoryAdapter(backend, retention_days=7, clock=lambda: now)

    await adapter.remember(_context(), "temporary fact")
    assert backend.add_calls[-1]["expiration_date"] == now + timedelta(days=7)
    with pytest.raises(ValueError, match="expiration"):
        await adapter.remember(_context(), "expired", expiration_date=now - timedelta(seconds=1))


@pytest.mark.anyio
async def test_backend_failures_use_product_safe_error() -> None:
    backend = FakeMem0()
    backend.fail = True
    adapter = AgentScopeUserMemoryAdapter(backend)

    with pytest.raises(MemoryBackendUnavailable, match="memory backend unavailable"):
        await adapter.search(_context(), "hello")


def test_scope_rejects_empty_identity_and_builds_stable_namespaces() -> None:
    with pytest.raises(ValueError, match="tenant_id"):
        UserMemoryScope(tenant_id="", user_id="user", agent_definition_id="agent")
    first = _context().scope
    second = _context(tenant_id="tenant-b").scope
    assert first.mem0_user_id != second.mem0_user_id
    assert "agent-a-" in first.mem0_agent_id


@pytest.mark.integration
@pytest.mark.anyio
async def test_mem0_qdrant_namespace_isolation_boundary() -> None:
    """Exercise the real Qdrant payload filter when integration services exist."""
    qdrant_url = os.getenv("AGENTSCOPE_INTEGRATION_QDRANT_URL")
    if not qdrant_url:
        pytest.skip("set AGENTSCOPE_INTEGRATION_QDRANT_URL for the real Mem0/Qdrant boundary")

    from qdrant_client import AsyncQdrantClient
    from qdrant_client.models import Distance, FieldCondition, Filter, MatchValue, PointStruct, VectorParams

    client = AsyncQdrantClient(url=qdrant_url)
    collection = "agentscope_mem0_" + uuid4().hex[:12]
    tenant_b_user = _context(tenant_id="tenant-b").scope.mem0_user_id
    try:
        await client.create_collection(
            collection_name=collection,
            vectors_config=VectorParams(size=2, distance=Distance.COSINE),
        )
        await client.upsert(
            collection_name=collection,
            points=[
                PointStruct(
                    id=1,
                    vector=[1.0, 0.0],
                    payload={"user_id": _context().scope.mem0_user_id, "agent_id": _context().scope.mem0_agent_id},
                ),
                PointStruct(
                    id=2,
                    vector=[1.0, 0.0],
                    payload={"user_id": tenant_b_user, "agent_id": _context().scope.mem0_agent_id},
                ),
            ],
        )
        response = await client.query_points(
            collection_name=collection,
            query=[1.0, 0.0],
            query_filter=Filter(
                must=[
                    FieldCondition(key="user_id", match=MatchValue(value=_context().scope.mem0_user_id)),
                    FieldCondition(key="agent_id", match=MatchValue(value=_context().scope.mem0_agent_id)),
                ]
            ),
            limit=10,
        )
        assert [point.id for point in response.points] == [1]
        assert tenant_b_user != _context().scope.mem0_user_id
    finally:
        await client.delete_collection(collection)
{%- else %}
"""AgentScope memory tests are not configured for this generated project."""
{%- endif %}
