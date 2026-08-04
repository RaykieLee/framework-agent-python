{%- if cookiecutter.use_agentscope and cookiecutter.enable_teams and cookiecutter.use_jwt %}
"""PostgreSQL repository for the Agent Definition control plane."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.agentscope_agent_definition import AgentDefinition, TenantAgentDefinition


async def list_published(db: AsyncSession) -> list[AgentDefinition]:
    result = await db.execute(
        select(AgentDefinition)
        .where(AgentDefinition.is_published.is_(True))
        .order_by(AgentDefinition.slug.asc(), AgentDefinition.version.desc())
    )
    return list(result.scalars().all())


async def get_published(
    db: AsyncSession, *, slug: str, version: int | None = None
) -> AgentDefinition | None:
    query = select(AgentDefinition).where(
        AgentDefinition.slug == slug,
        AgentDefinition.is_published.is_(True),
    )
    if version is not None:
        query = query.where(AgentDefinition.version == version)
    query = query.order_by(AgentDefinition.version.desc())
    result = await db.execute(query)
    return result.scalars().first()


async def list_bindings(db: AsyncSession, *, organization_id: UUID) -> list[TenantAgentDefinition]:
    result = await db.execute(
        select(TenantAgentDefinition)
        .where(TenantAgentDefinition.organization_id == organization_id)
        .order_by(TenantAgentDefinition.definition_slug.asc())
    )
    return list(result.scalars().all())


async def get_binding(
    db: AsyncSession, *, organization_id: UUID, definition_slug: str
) -> TenantAgentDefinition | None:
    result = await db.execute(
        select(TenantAgentDefinition).where(
            TenantAgentDefinition.organization_id == organization_id,
            TenantAgentDefinition.definition_slug == definition_slug,
        )
    )
    return result.scalar_one_or_none()


async def create_binding(
    db: AsyncSession,
    *,
    organization_id: UUID,
    definition: AgentDefinition,
    enabled: bool,
    limit_overrides: dict[str, int],
    enabled_by_user_id: UUID,
) -> TenantAgentDefinition:
    binding = TenantAgentDefinition(
        organization_id=organization_id,
        definition_slug=definition.slug,
        agent_definition_id=definition.id,
        enabled=enabled,
        limit_overrides=limit_overrides,
        enabled_by_user_id=enabled_by_user_id,
    )
    db.add(binding)
    await db.flush()
    await db.refresh(binding)
    return binding


async def update_binding(
    db: AsyncSession,
    binding: TenantAgentDefinition,
    *,
    definition: AgentDefinition,
    enabled: bool,
    limit_overrides: dict[str, int],
    enabled_by_user_id: UUID,
) -> TenantAgentDefinition:
    binding.agent_definition_id = definition.id
    binding.enabled = enabled
    binding.limit_overrides = limit_overrides
    binding.enabled_by_user_id = enabled_by_user_id
    await db.flush()
    await db.refresh(binding)
    return binding


__all__ = [
    "create_binding",
    "get_binding",
    "get_published",
    "list_bindings",
    "list_published",
    "update_binding",
]
{%- else %}
"""AgentScope Agent Definition repository — not configured."""
{%- endif %}
