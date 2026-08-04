{%- if cookiecutter.use_agentscope and cookiecutter.use_jwt and cookiecutter.enable_teams %}
"""Generated AgentScope control-plane wiring.

The generated route is deliberately thin, but it must still construct the
runtime with server-owned tenant identity and an explicit persistence factory.
This module is the single injection point for production adapters; local tests
use one process-local store only outside ``production``.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import AuthorizationError, NotFoundError
from app.db.models.organization import OrgRole, Organization
from app.db.models.user import User
from app.repositories import conversation_repo, member_repo, organization_repo
from app.services.agentscope_durable_session import (
    AgentScopeDurableSession,
    DurableSessionStore,
    InMemoryDurableSessionStore,
)


class AgentScopeRuntimeUnavailable(RuntimeError):
    """Raised when production adapters have not been configured."""


@dataclass(frozen=True, slots=True)
class AgentScopeTenantContext:
    """Immutable tenant identity resolved from authenticated server state."""

    tenant_id: str
    user_id: str
    role: str
    is_personal: bool


@dataclass(frozen=True, slots=True)
class AgentScopeExecutionResources:
    """Per-turn adapters bound to one active tenant."""

    middlewares: tuple[Any, ...] = ()
    knowledge_base: Any | None = None
    memory_middleware: Any | None = None
    delegation_policy: Any | None = None
    personal_connections: tuple[Any, ...] = ()


@dataclass(frozen=True, slots=True)
class TenantBoundResource:
    """Control-plane binding marker used until a deployment supplies its adapter."""

    kind: str
    tenant_id: str
    user_id: str


DurableStoreFactory = Callable[[], DurableSessionStore]
ResourceFactory = Callable[[AgentScopeTenantContext], Awaitable[AgentScopeExecutionResources] | AgentScopeExecutionResources]
TeamFrameHandler = Callable[[AgentScopeTenantContext, dict[str, Any]], Awaitable[dict[str, Any]]]


def _default_resource_factory(context: AgentScopeTenantContext) -> AgentScopeExecutionResources:
    """Create explicit tenant-bound control-plane resources before adapters are injected."""
    return AgentScopeExecutionResources(
        knowledge_base=TenantBoundResource("knowledge_base", context.tenant_id, context.user_id),
        memory_middleware=TenantBoundResource("mem0_memory", context.tenant_id, context.user_id),
        delegation_policy=TenantBoundResource("delegation", context.tenant_id, context.user_id),
        personal_connections=(TenantBoundResource("personal_connections", context.tenant_id, context.user_id),),
    )


@dataclass(slots=True)
class AgentScopeRuntimeWiring:
    """Production injection container for AgentScope's control-plane seams."""

    durable_store_factory: DurableStoreFactory
    resource_factory: ResourceFactory | None = _default_resource_factory
    knowledge_factory: Callable[[AgentScopeTenantContext], Any] | None = None
    memory_middleware_factory: Callable[[AgentScopeTenantContext], Any] | None = None
    delegation_factory: Callable[[AgentScopeTenantContext], Any] | None = None
    personal_connections_factory: Callable[[AgentScopeTenantContext], Any] | None = None
    member_exit_cleanup: Any | None = None
    tenant_purge_service: Any | None = None
    team_frame_handler: TeamFrameHandler | None = None
    team_run_coordinator: Any | None = None

    def durable_session(self, context: AgentScopeTenantContext, conversation_id: str) -> AgentScopeDurableSession:
        return AgentScopeDurableSession(
            self.durable_store_factory(),
            tenant_id=context.tenant_id,
            conversation_id=conversation_id,
        )

    async def execution_resources(self, context: AgentScopeTenantContext) -> AgentScopeExecutionResources:
        if self.resource_factory is None:
            resources = AgentScopeExecutionResources(
                knowledge_base=TenantBoundResource("knowledge_base", context.tenant_id, context.user_id),
                memory_middleware=TenantBoundResource("mem0_memory", context.tenant_id, context.user_id),
                delegation_policy=TenantBoundResource("delegation", context.tenant_id, context.user_id),
                personal_connections=(TenantBoundResource("personal_connections", context.tenant_id, context.user_id),),
            )
        else:
            value = self.resource_factory(context)
            resources = await value if hasattr(value, "__await__") else value
        knowledge = self.knowledge_factory(context) if self.knowledge_factory else resources.knowledge_base
        memory = self.memory_middleware_factory(context) if self.memory_middleware_factory else resources.memory_middleware
        delegation = self.delegation_factory(context) if self.delegation_factory else resources.delegation_policy
        connections = self.personal_connections_factory(context) if self.personal_connections_factory else resources.personal_connections
        middlewares = tuple(resources.middlewares)
        if memory is not None and not isinstance(memory, TenantBoundResource) and memory not in middlewares:
            middlewares = (*middlewares, memory)
        return AgentScopeExecutionResources(
            middlewares=middlewares,
            knowledge_base=knowledge,
            memory_middleware=memory,
            delegation_policy=delegation,
            personal_connections=tuple(connections or ()),
        )

    async def team_frame(self, context: AgentScopeTenantContext, frame: dict[str, Any]) -> dict[str, Any]:
        """Dispatch product team control frames to the configured run/ledger seam."""
        if self.team_frame_handler is not None:
            return await self.team_frame_handler(context, frame)
        coordinator = self.team_run_coordinator
        if coordinator is None:
            raise AgentScopeRuntimeUnavailable("AgentScope team runtime is not configured")
        handler = getattr(coordinator, "handle_frame", None)
        if handler is None:
            raise AgentScopeRuntimeUnavailable("AgentScope TeamRun coordinator has no frame handler")
        result = handler(context, frame)
        return await result if hasattr(result, "__await__") else result


_configured: AgentScopeRuntimeWiring | None = None
_in_process_store = InMemoryDurableSessionStore()


class _UnavailableCleanup:
    async def run(self, _request: Any) -> None:
        raise AgentScopeRuntimeUnavailable("AgentScope member-exit adapters are not configured")


class _UnavailablePurge:
    async def request(self, _request: Any) -> None:
        raise AgentScopeRuntimeUnavailable("AgentScope tenant-purge adapters are not configured")


class _UnavailableTeamRun:
    async def handle_frame(self, _context: AgentScopeTenantContext, _frame: dict[str, Any]) -> dict[str, Any]:
        raise AgentScopeRuntimeUnavailable("AgentScope TeamRun adapters are not configured")


def configure_agentscope_runtime(wiring: AgentScopeRuntimeWiring) -> None:
    """Install PostgreSQL/Redis, memory, KB, team, and cleanup adapters at boot."""
    global _configured
    _configured = wiring


def get_agentscope_runtime() -> AgentScopeRuntimeWiring:
    """Return configured wiring, or a safe non-production test fallback."""
    if _configured is not None:
        if settings.ENVIRONMENT == "production" and (
            _configured.member_exit_cleanup is None or _configured.tenant_purge_service is None
        ):
            raise AgentScopeRuntimeUnavailable("AgentScope cleanup and purge adapters are required in production")
        return _configured
    if settings.ENVIRONMENT != "production" or settings.AGENTSCOPE_ALLOW_IN_PROCESS_FALLBACK:
        return AgentScopeRuntimeWiring(
            durable_store_factory=lambda: _in_process_store,
            member_exit_cleanup=_UnavailableCleanup(),
            tenant_purge_service=_UnavailablePurge(),
            team_run_coordinator=_UnavailableTeamRun(),
        )
    raise AgentScopeRuntimeUnavailable("AgentScope production adapters are not configured")


async def resolve_tenant_context(
    db: AsyncSession,
    user: User,
    requested_organization_id: str | None = None,
) -> AgentScopeTenantContext:
    """Resolve and authorize the active tenant; never trust frame tenant fields."""
    organization: Organization | None
    if requested_organization_id:
        try:
            organization_id = UUID(str(requested_organization_id))
        except ValueError as exc:
            raise NotFoundError(message="Tenant not found or access denied") from exc
        membership = await member_repo.get(db, organization_id=organization_id, user_id=user.id)
        if membership is None:
            raise NotFoundError(message="Tenant not found or access denied")
        organization = await organization_repo.get_by_id(db, organization_id)
        if organization is None:
            raise NotFoundError(message="Tenant not found or access denied")
        role = str(membership.role)
    else:
        organization = await organization_repo.get_personal_for_user(db, user.id)
        if organization is None:
            raise NotFoundError(message="Personal Tenant not found")
        membership = await member_repo.get(db, organization_id=organization.id, user_id=user.id)
        role = str(getattr(membership, "role", OrgRole.OWNER.value))
    return AgentScopeTenantContext(
        tenant_id=str(organization.id),
        user_id=str(user.id),
        role=role,
        is_personal=bool(organization.is_personal),
    )


async def validate_conversation_tenant(
    db: AsyncSession,
    context: AgentScopeTenantContext,
    conversation_id: str,
) -> None:
    """Reject a conversation outside the server-resolved tenant/user scope."""
    try:
        conversation = await conversation_repo.get_conversation_by_id(db, UUID(str(conversation_id)))
    except ValueError as exc:
        raise NotFoundError(message="Conversation not found") from exc
    if conversation is None or str(getattr(conversation, "user_id", "")) != context.user_id:
        raise NotFoundError(message="Conversation not found")
    owner_tenant = getattr(conversation, "organization_id", None)
    if owner_tenant is not None and str(owner_tenant) != context.tenant_id:
        raise AuthorizationError(message="Conversation does not belong to the active tenant")


__all__ = [
    "AgentScopeExecutionResources",
    "AgentScopeRuntimeUnavailable",
    "AgentScopeRuntimeWiring",
    "AgentScopeTenantContext",
    "TenantBoundResource",
    "configure_agentscope_runtime",
    "get_agentscope_runtime",
    "resolve_tenant_context",
    "validate_conversation_tenant",
]
{%- else %}
"""AgentScope runtime wiring is not configured."""
{%- endif %}
