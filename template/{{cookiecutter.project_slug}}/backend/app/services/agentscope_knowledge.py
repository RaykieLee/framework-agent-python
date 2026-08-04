{%- if cookiecutter.use_agentscope and cookiecutter.enable_rag and cookiecutter.enable_teams %}
"""Control-plane knowledge-base adapter for the AgentScope runtime.

AgentScope receives a read-only retrieval seam from this module.  Knowledge
base identity, lifecycle, ingestion, and authorization remain in the template
control plane; the runtime never receives a collection name or an arbitrary
vector filter from a caller or a model.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Protocol
from uuid import UUID

from app.db.models.knowledge_base import KBScope, KnowledgeBase
from app.services.rag.models import SearchResult
from app.services.rag.retrieval import BaseRetrievalService


class KnowledgeBaseAccessResolver(Protocol):
    """Control-plane boundary used to resolve visible KB records."""

    async def get_accessible(
        self,
        db: Any,
        *,
        user_id: UUID,
        organization_id: UUID | None = None,
    ) -> list[KnowledgeBase]: ...


class ControlPlaneKnowledgeBaseError(PermissionError):
    """Base error for an invalid or unauthorized runtime KB request."""


class ReadOnlyKnowledgeBaseError(ControlPlaneKnowledgeBaseError):
    """AgentScope cannot create, ingest, update, or delete KB data."""


class InvalidTenantContext(ControlPlaneKnowledgeBaseError):
    """A retrieval request did not carry one active tenant."""


@dataclass(frozen=True, slots=True)
class AgentScopeKnowledgeContext:
    """Authoritative identity for one AgentScope retrieval operation."""

    tenant_id: str
    actor_user_id: str
    organization_id: str | None = None

    def __post_init__(self) -> None:
        if not str(self.tenant_id).strip():
            raise InvalidTenantContext("AgentScope KB retrieval requires an active tenant")
        if not str(self.actor_user_id).strip():
            raise InvalidTenantContext("AgentScope KB retrieval requires an actor user")


@dataclass(frozen=True, slots=True)
class KnowledgeBaseHandle:
    """An opaque, server-resolved handle safe to pass to AgentScope."""

    tenant_id: str
    knowledge_base_id: str
    collection_name: str
    scope: str
    metadata_filter: Mapping[str, str]

    @property
    def filter_expression(self) -> str:
        """Portable expression consumed by vector backends as defense in depth."""
        return (
            f'metadata.tenant_id == "{self.metadata_filter["tenant_id"]}" '
            f'AND metadata.knowledge_base_id == "{self.metadata_filter["knowledge_base_id"]}"'
        )


@dataclass(frozen=True, slots=True)
class AgentScopeKnowledgeResult:
    """Retrieval result with a citation tied to a resolved KB handle."""

    content: str
    score: float
    knowledge_base_id: str
    collection_name: str
    document_id: str | None
    metadata: Mapping[str, Any]

    @property
    def citation(self) -> dict[str, str | None]:
        return {
            "knowledge_base_id": self.knowledge_base_id,
            "collection_name": self.collection_name,
            "document_id": self.document_id,
        }


class AgentScopeKnowledgeBaseAdapter:
    """Read-only AgentScope RAG adapter backed by template KB records."""

    def __init__(
        self,
        db: Any,
        retrieval: BaseRetrievalService,
        *,
        access_resolver: KnowledgeBaseAccessResolver,
    ) -> None:
        self.db = db
        self.retrieval = retrieval
        self.access_resolver = access_resolver

    @classmethod
    def from_control_plane(
        cls, db: Any, retrieval: BaseRetrievalService
    ) -> "AgentScopeKnowledgeBaseAdapter":
        """Construct the adapter with the generated KB repository."""
        from app.repositories import knowledge_base as knowledge_base_repo

        return cls(db, retrieval, access_resolver=knowledge_base_repo)

    async def resolve_handles(
        self,
        context: AgentScopeKnowledgeContext,
        knowledge_base_ids: Sequence[str | UUID],
    ) -> tuple[KnowledgeBaseHandle, ...]:
        """Resolve public KB IDs to authorized, tenant-bound runtime handles.

        An empty selection intentionally resolves to no handles.  It never
        means "all collections", and collection names supplied by a caller are
        not accepted by this seam.
        """
        if not knowledge_base_ids:
            return ()
        try:
            actor_id = UUID(str(context.actor_user_id))
            organization_id = (
                UUID(str(context.organization_id)) if context.organization_id else None
            )
        except ValueError as exc:
            raise InvalidTenantContext("Tenant and actor IDs must be UUIDs") from exc

        accessible = await self.access_resolver.get_accessible(
            self.db,
            user_id=actor_id,
            organization_id=organization_id,
        )
        wanted = {str(item) for item in knowledge_base_ids}
        handles: list[KnowledgeBaseHandle] = []
        for kb in accessible:
            if str(kb.id) not in wanted:
                continue
            self._assert_tenant_scope(kb, context)
            metadata_tenant = "platform" if kb.scope == KBScope.APP.value else str(context.tenant_id)
            handles.append(
                KnowledgeBaseHandle(
                    tenant_id=str(context.tenant_id),
                    knowledge_base_id=str(kb.id),
                    collection_name=kb.collection_name,
                    scope=str(kb.scope),
                    metadata_filter={
                        "tenant_id": metadata_tenant,
                        "knowledge_base_id": str(kb.id),
                    },
                )
            )
        return tuple(handles)

    async def query(
        self,
        context: AgentScopeKnowledgeContext,
        *,
        query: str,
        knowledge_base_ids: Sequence[str | UUID],
        limit: int = 5,
        min_score: float = 0.0,
    ) -> list[AgentScopeKnowledgeResult]:
        """Retrieve only authorized chunks and return citation-bearing results."""
        if limit < 1:
            raise ValueError("limit must be positive")
        handles = await self.resolve_handles(context, knowledge_base_ids)
        results: list[AgentScopeKnowledgeResult] = []
        for handle in handles:
            hits = await self.retrieval.retrieve(
                query=query,
                collection_name=handle.collection_name,
                limit=limit,
                min_score=min_score,
                filter=handle.filter_expression,
            )
            for hit in hits:
                if not self._matches_handle(hit, handle):
                    continue
                results.append(
                    AgentScopeKnowledgeResult(
                        content=hit.content,
                        score=hit.score,
                        knowledge_base_id=handle.knowledge_base_id,
                        collection_name=handle.collection_name,
                        document_id=hit.parent_doc_id,
                        metadata=dict(hit.metadata),
                    )
                )
        results.sort(key=lambda result: result.score, reverse=True)
        return results[:limit]

    def build_search_tool(
        self,
        context: AgentScopeKnowledgeContext,
        *,
        knowledge_base_ids: Sequence[str | UUID],
        limit: int = 5,
    ) -> Callable[[str], Awaitable[list[AgentScopeKnowledgeResult]]]:
        """Build an AgentScope-compatible callable with fixed server context."""

        async def search(query: str) -> list[AgentScopeKnowledgeResult]:
            return await self.query(
                context,
                query=query,
                knowledge_base_ids=knowledge_base_ids,
                limit=limit,
            )

        return search

    async def index(self, *_args: Any, **_kwargs: Any) -> None:
        """Reject runtime-owned indexing; ingestion belongs to the control plane."""
        raise ReadOnlyKnowledgeBaseError(
            "AgentScope KB indexing is disabled; use the Control Plane ingestion API"
        )

    async def delete(self, *_args: Any, **_kwargs: Any) -> None:
        """Reject runtime-owned deletion; lifecycle belongs to the control plane."""
        raise ReadOnlyKnowledgeBaseError(
            "AgentScope KB deletion is disabled; use the Control Plane lifecycle API"
        )

    @staticmethod
    def _assert_tenant_scope(kb: KnowledgeBase, context: AgentScopeKnowledgeContext) -> None:
        tenant = str(context.tenant_id)
        if kb.scope == KBScope.APP.value:
            return
        if kb.scope == KBScope.ORG.value and str(kb.organization_id) == tenant:
            return
        # Personal KBs are owned by the actor and remain bound to the active
        # personal tenant when the control-plane row carries an organization.
        if kb.scope == KBScope.PERSONAL.value and str(kb.owner_user_id) == str(
            context.actor_user_id
        ) and (kb.organization_id is None or str(kb.organization_id) == tenant):
            return
        raise InvalidTenantContext("Knowledge base is outside the active tenant")

    @staticmethod
    def _matches_handle(hit: SearchResult, handle: KnowledgeBaseHandle) -> bool:
        """Apply a second application-side filter after vector retrieval."""
        metadata = hit.metadata
        return (
            str(metadata.get("tenant_id", "")) == handle.metadata_filter["tenant_id"]
            and str(metadata.get("knowledge_base_id", ""))
            == handle.metadata_filter["knowledge_base_id"]
        )


__all__ = [
    "AgentScopeKnowledgeBaseAdapter",
    "AgentScopeKnowledgeContext",
    "AgentScopeKnowledgeResult",
    "ControlPlaneKnowledgeBaseError",
    "InvalidTenantContext",
    "KnowledgeBaseHandle",
    "ReadOnlyKnowledgeBaseError",
]
{%- else %}
"""AgentScope knowledge-base adapter is not configured."""
{%- endif %}
