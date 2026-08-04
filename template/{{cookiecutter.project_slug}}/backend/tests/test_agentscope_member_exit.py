{%- if cookiecutter.use_agentscope and cookiecutter.enable_teams %}
"""Contract tests for private-state cleanup when a Tenant member leaves."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any

import pytest

from app.services.agentscope_member_exit import (
    AllowMemberExitAuthorizer,
    CleanupStep,
    InMemoryAuditSink,
    InMemoryCleanupLedger,
    InMemoryMembershipRevoker,
    MemberExitAuthorizationError,
    MemberExitCleanupIncomplete,
    MemberExitCleanupService,
    MemberExitRequest,
    ProductionMemberExitAdapters,
    TenantConversationAccess,
    build_production_resource_adapters,
)


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


class RecordingResource:
    """Fake at an external-store seam; deletion is idempotent by design."""

    def __init__(self, name: str, calls: list[tuple[str, str, str]], *, fail: bool = False) -> None:
        self.name = name
        self.calls = calls
        self.fail = fail

    async def delete_for_member(self, *, tenant_id: str, user_id: str) -> None:
        self.calls.append((self.name, tenant_id, user_id))
        if self.fail:
            self.fail = False
            raise RuntimeError(f"{self.name} unavailable")


def _request(request_id: str = "leave-1") -> MemberExitRequest:
    return MemberExitRequest(
        tenant_id="tenant-a",
        user_id="user-a",
        actor_user_id="user-a",
        request_id=request_id,
    )


def _service(
    calls: list[tuple[str, str, str]],
    *,
    memory_fails_once: bool = False,
) -> tuple[MemberExitCleanupService, InMemoryMembershipRevoker, InMemoryAuditSink]:
    membership = InMemoryMembershipRevoker()
    audit = InMemoryAuditSink()
    resources = {
        name: RecordingResource(name, calls, fail=name == "memory" and memory_fails_once)
        for name in ("connections", "memory", "sessions", "teams", "workspace")
    }
    service = MemberExitCleanupService(
        membership=membership,
        personal_connections=resources["connections"],
        user_memory=resources["memory"],
        sessions=resources["sessions"],
        execution_teams=resources["teams"],
        workspaces=resources["workspace"],
        ledger=InMemoryCleanupLedger(),
        audit=audit,
        authorizer=AllowMemberExitAuthorizer(),
        clock=lambda: datetime(2026, 1, 1, tzinfo=UTC),
    )
    return service, membership, audit


@pytest.mark.anyio
async def test_exit_revokes_access_first_and_retains_tenant_conversations() -> None:
    calls: list[tuple[str, str, str]] = []
    service, membership, audit = _service(calls)

    report = await service.run(_request())

    assert report.complete
    assert report.tenant_conversations_retained is True
    assert set(report.completed_steps) == set(CleanupStep)
    assert await membership.is_revoked(tenant_id="tenant-a", user_id="user-a")
    assert [name for name, _, _ in calls] == [
        "connections",
        "memory",
        "sessions",
        "teams",
        "workspace",
    ]
    assert [event.event for event in audit.events[:2]] == ["started", "completed"]
    assert all(event.operation_id == "member-exit:tenant-a:user-a" for event in audit.events)

    guard = TenantConversationAccess(membership)
    for action in ("read", "subscribe", "execute", "mutate"):
        with pytest.raises(MemberExitAuthorizationError):
            await guard.authorize(tenant_id="tenant-a", user_id="user-a", action=action)


@pytest.mark.anyio
async def test_partial_failure_is_audited_and_retry_only_replays_failed_step() -> None:
    calls: list[tuple[str, str, str]] = []
    service, _membership, _audit = _service(calls, memory_fails_once=True)

    with pytest.raises(MemberExitCleanupIncomplete) as first:
        await service.run(_request())
    assert first.value.report.failed_steps == (CleanupStep.USER_MEMORY,)
    first_call_count = len(calls)

    second = await service.run(_request("job-retry"))
    assert second.complete
    # All successful steps are ledgered; only Mem0/Qdrant is retried.
    assert len(calls) == first_call_count + 1
    assert calls[-1][0] == "memory"

    third = await service.run(_request("duplicate"))
    assert third.complete
    assert len(calls) == first_call_count + 1


@pytest.mark.anyio
async def test_authorization_failure_revokes_nothing() -> None:
    calls: list[tuple[str, str, str]] = []
    service, membership, _audit = _service(calls)

    class Deny:
        async def authorize(self, request: MemberExitRequest) -> None:
            raise MemberExitAuthorizationError(f"not allowed: {request.actor_user_id}")

    service.authorizer = Deny()
    with pytest.raises(MemberExitAuthorizationError):
        await service.run(_request())
    assert calls == []
    assert not await membership.is_revoked(tenant_id="tenant-a", user_id="user-a")


class _ProductionRepo:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, str]] = []

    async def revoke_membership(self, **kwargs: str) -> None:
        self.calls.append(("revoke", kwargs["tenant_id"], kwargs["user_id"]))

    async def delete_personal_connections(self, **kwargs: str) -> None:
        self.calls.append(("connections", kwargs["tenant_id"], kwargs["user_id"]))

    async def delete_sessions(self, **kwargs: str) -> None:
        self.calls.append(("postgres_sessions", kwargs["tenant_id"], kwargs["user_id"]))

    async def load_completed_steps(self, **kwargs: Any) -> set[CleanupStep]:
        del kwargs
        return set()

    async def mark_cleanup_step(self, **kwargs: Any) -> None:
        del kwargs


class _RedisRepo:
    def __init__(self, calls: list[tuple[str, str, str]]) -> None:
        self.calls = calls

    async def delete_sessions(self, **kwargs: str) -> None:
        self.calls.append(("redis_sessions", kwargs["tenant_id"], kwargs["user_id"]))

    async def delete_execution_teams(self, **kwargs: str) -> None:
        self.calls.append(("teams", kwargs["tenant_id"], kwargs["user_id"]))


class _QdrantRepo:
    def __init__(self, calls: list[tuple[str, str, str]]) -> None:
        self.calls = calls

    async def delete_user_memory(self, **kwargs: str) -> None:
        self.calls.append(("qdrant_memory", kwargs["tenant_id"], kwargs["user_id"]))


class _WorkspaceRepo:
    def __init__(self, calls: list[tuple[str, str, str]]) -> None:
        self.calls = calls

    async def delete_workspaces(self, **kwargs: str) -> None:
        self.calls.append(("workspace", kwargs["tenant_id"], kwargs["user_id"]))


@pytest.mark.integration
@pytest.mark.anyio
async def test_production_adapters_cover_postgres_redis_qdrant_and_workspace() -> None:
    """The infrastructure seam is explicit even when live services are absent."""
    calls: list[tuple[str, str, str]] = []
    postgres = _ProductionRepo()
    redis = _RedisRepo(calls)
    qdrant = _QdrantRepo(calls)
    workspace = _WorkspaceRepo(calls)
    connections, memory, sessions, teams, workspaces = build_production_resource_adapters(
        ProductionMemberExitAdapters(
            postgres=postgres,
            redis=redis,
            qdrant=qdrant,
            workspace=workspace,
        )
    )

    await connections.delete_for_member(tenant_id="tenant-a", user_id="user-a")
    await memory.delete_for_member(tenant_id="tenant-a", user_id="user-a")
    await sessions.delete_for_member(tenant_id="tenant-a", user_id="user-a")
    await teams.delete_for_member(tenant_id="tenant-a", user_id="user-a")
    await workspaces.delete_for_member(tenant_id="tenant-a", user_id="user-a")

    assert postgres.calls == [("connections", "tenant-a", "user-a"), ("postgres_sessions", "tenant-a", "user-a")]
    assert calls == [
        ("qdrant_memory", "tenant-a", "user-a"),
        ("redis_sessions", "tenant-a", "user-a"),
        ("teams", "tenant-a", "user-a"),
        ("workspace", "tenant-a", "user-a"),
    ]
{%- else %}
"""AgentScope member-exit tests are not configured."""
{%- endif %}
