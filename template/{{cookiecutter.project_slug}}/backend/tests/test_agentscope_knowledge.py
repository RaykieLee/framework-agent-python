{%- if cookiecutter.use_agentscope and cookiecutter.enable_rag and cookiecutter.enable_teams %}
"""Contract tests for the Control Plane → AgentScope KB adapter."""

from __future__ import annotations

import os
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest

from app.services.agentscope_knowledge import (
    AgentScopeKnowledgeBaseAdapter,
    AgentScopeKnowledgeContext,
    InvalidTenantContext,
    ReadOnlyKnowledgeBaseError,
)
from app.services.rag.models import SearchResult


TENANT_A = str(uuid4())
TENANT_B = str(uuid4())
ACTOR = str(uuid4())
KB_ORG = uuid4()
KB_PERSONAL = uuid4()
KB_PLATFORM = uuid4()


class FakeResolver:
    def __init__(self, records: list[SimpleNamespace]) -> None:
        self.records = records

    async def get_accessible(self, _db, *, user_id: UUID, organization_id: UUID | None = None):
        assert str(user_id) == ACTOR
        return self.records


class FakeRetrieval:
    def __init__(self, results: dict[str, list[SearchResult]]) -> None:
        self.results = results
        self.filters: list[str] = []

    async def retrieve(self, *, query, collection_name, limit, min_score, filter):
        self.filters.append(filter)
        return self.results.get(collection_name, [])[:limit]


def _kb(kb_id: UUID, *, scope: str, collection: str, org: str | None, owner: str | None):
    return SimpleNamespace(
        id=kb_id,
        scope=scope,
        collection_name=collection,
        organization_id=UUID(org) if org else None,
        owner_user_id=UUID(owner) if owner else None,
    )


def _adapter(retrieval: FakeRetrieval, records: list[SimpleNamespace]):
    return AgentScopeKnowledgeBaseAdapter(
        object(), retrieval, access_resolver=FakeResolver(records)
    )


@pytest.fixture
def context() -> AgentScopeKnowledgeContext:
    return AgentScopeKnowledgeContext(
        tenant_id=TENANT_A,
        actor_user_id=ACTOR,
        organization_id=TENANT_A,
    )


@pytest.mark.anyio
async def test_query_resolves_authorized_scopes_and_adds_citations(context):
    records = [
        _kb(KB_ORG, scope="org", collection="org_docs", org=TENANT_A, owner=None),
        _kb(KB_PERSONAL, scope="personal", collection="personal_docs", org=TENANT_A, owner=ACTOR),
        _kb(KB_PLATFORM, scope="app", collection="platform_docs", org=None, owner=None),
    ]
    retrieval = FakeRetrieval(
        {
            "org_docs": [
                SearchResult(
                    content="org answer",
                    score=0.9,
                    parent_doc_id="doc-org",
                    metadata={"tenant_id": TENANT_A, "knowledge_base_id": str(KB_ORG)},
                )
            ],
            "personal_docs": [
                SearchResult(
                    content="personal answer",
                    score=0.8,
                    parent_doc_id="doc-personal",
                    metadata={"tenant_id": TENANT_A, "knowledge_base_id": str(KB_PERSONAL)},
                )
            ],
        }
    )
    result = await _adapter(retrieval, records).query(
        context,
        query="answer",
        knowledge_base_ids=[str(KB_ORG), str(KB_PERSONAL)],
    )

    assert [item.content for item in result] == ["org answer", "personal answer"]
    assert result[0].citation == {
        "knowledge_base_id": str(KB_ORG),
        "collection_name": "org_docs",
        "document_id": "doc-org",
    }
    assert all("metadata.tenant_id" in expression for expression in retrieval.filters)
    assert all("metadata.knowledge_base_id" in expression for expression in retrieval.filters)


@pytest.mark.anyio
async def test_forged_id_and_cross_tenant_kb_are_not_retrievable(context):
    foreign = _kb(
        uuid4(), scope="org", collection="foreign_docs", org=TENANT_B, owner=None
    )
    retrieval = FakeRetrieval(
        {
            "foreign_docs": [
                SearchResult(
                    content="secret",
                    score=1.0,
                    metadata={"tenant_id": TENANT_B, "knowledge_base_id": str(foreign.id)},
                )
            ]
        }
    )
    adapter = _adapter(retrieval, [foreign])

    with pytest.raises(InvalidTenantContext):
        await adapter.query(context, query="secret", knowledge_base_ids=[str(foreign.id)])
    assert await adapter.query(
        context, query="secret", knowledge_base_ids=[str(uuid4())]
    ) == []


@pytest.mark.anyio
async def test_backend_result_without_mandatory_metadata_is_denied(context):
    record = _kb(KB_ORG, scope="org", collection="org_docs", org=TENANT_A, owner=None)
    retrieval = FakeRetrieval(
        {"org_docs": [SearchResult(content="legacy", score=1.0, metadata={})]}
    )

    assert await _adapter(retrieval, [record]).query(
        context, query="legacy", knowledge_base_ids=[str(KB_ORG)]
    ) == []


@pytest.mark.anyio
async def test_platform_resource_uses_platform_metadata_marker(context):
    record = _kb(KB_PLATFORM, scope="app", collection="platform_docs", org=None, owner=None)
    retrieval = FakeRetrieval(
        {
            "platform_docs": [
                SearchResult(
                    content="platform answer",
                    score=0.7,
                    metadata={"tenant_id": "platform", "knowledge_base_id": str(KB_PLATFORM)},
                )
            ]
        }
    )
    result = await _adapter(retrieval, [record]).query(
        context, query="platform", knowledge_base_ids=[str(KB_PLATFORM)]
    )
    assert [item.content for item in result] == ["platform answer"]
    assert "platform" in retrieval.filters[0]


@pytest.mark.anyio
async def test_runtime_cannot_index_or_delete(context):
    adapter = _adapter(FakeRetrieval({}), [])
    with pytest.raises(ReadOnlyKnowledgeBaseError):
        await adapter.index(context, object())
    with pytest.raises(ReadOnlyKnowledgeBaseError):
        await adapter.delete(context, str(KB_ORG))


def test_missing_tenant_context_is_rejected():
    with pytest.raises(InvalidTenantContext):
        AgentScopeKnowledgeContext(tenant_id="", actor_user_id=ACTOR)


@pytest.mark.integration
@pytest.mark.anyio
async def test_postgresql_qdrant_isolation_boundary():
    """Run the real-store isolation contract when integration services are supplied."""
    if not os.getenv("AGENTSCOPE_INTEGRATION_DATABASE_URL"):
        pytest.skip("set AGENTSCOPE_INTEGRATION_DATABASE_URL and AGENTSCOPE_INTEGRATION_QDRANT_URL")
    qdrant_url = os.getenv("AGENTSCOPE_INTEGRATION_QDRANT_URL")
    if not qdrant_url:
        pytest.skip("set AGENTSCOPE_INTEGRATION_DATABASE_URL and AGENTSCOPE_INTEGRATION_QDRANT_URL")

    from qdrant_client import AsyncQdrantClient
    from qdrant_client.models import (
        Distance,
        FieldCondition,
        Filter,
        MatchValue,
        PointStruct,
        VectorParams,
    )

    client = AsyncQdrantClient(url=qdrant_url)
    collection = f"agentscope_kb_{uuid4().hex[:12]}"
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
                    payload={"metadata": {"tenant_id": TENANT_A, "knowledge_base_id": str(KB_ORG)}},
                ),
                PointStruct(
                    id=2,
                    vector=[1.0, 0.0],
                    payload={"metadata": {"tenant_id": TENANT_B, "knowledge_base_id": str(KB_ORG)}},
                ),
            ],
        )
        response = await client.query_points(
            collection_name=collection,
            query=[1.0, 0.0],
            query_filter=Filter(
                must=[
                    FieldCondition(
                        key="metadata.tenant_id", match=MatchValue(value=TENANT_A)
                    ),
                    FieldCondition(
                        key="metadata.knowledge_base_id",
                        match=MatchValue(value=str(KB_ORG)),
                    ),
                ]
            ),
            limit=10,
        )
        assert [point.id for point in response.points] == [1]
    finally:
        await client.delete_collection(collection)
{%- else %}
"""AgentScope KB adapter tests are not configured."""
{%- endif %}
