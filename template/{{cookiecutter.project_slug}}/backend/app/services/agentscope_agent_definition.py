{%- if cookiecutter.use_agentscope and cookiecutter.enable_teams and cookiecutter.use_jwt %}
"""Tenant authorization and lifecycle for platform Agent Definitions."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthorizationError, NotFoundError, ValidationError
from app.db.models.agentscope_agent_definition import AgentDefinition, TenantAgentDefinition
from app.repositories import agentscope_agent_definition as definition_repo
from app.repositories import member as member_repo
from app.schemas.agentscope_agent_definition import (
    AgentDefinitionList,
    AgentDefinitionRead,
    AgentDefinitionRuntime,
    AgentDefinitionUpdate,
)


class AgentDefinitionService:
    """Control-plane facade; no AgentScope native API is exposed here."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def _membership(self, organization_id: UUID, user_id: UUID):
        membership = await member_repo.get(
            self.db, organization_id=organization_id, user_id=user_id
        )
        if not membership:
            raise NotFoundError(
                message="Organization not found or access denied",
                details={"organization_id": str(organization_id)},
            )
        return membership

    async def _require_admin(self, organization_id: UUID, user_id: UUID):
        membership = await self._membership(organization_id, user_id)
        if membership.role not in {"owner", "admin"}:
            raise AuthorizationError(message="Only Owner or Admin can manage Agent Definitions")
        return membership

    @staticmethod
    def _bounded_limits(
        definition: AgentDefinition, overrides: dict[str, int]
    ) -> dict[str, int]:
        published = definition.limits or {}
        unknown = set(overrides) - set(published)
        if unknown:
            raise ValidationError(
                message="Unknown Agent Definition limit",
                details={"keys": sorted(unknown)},
            )
        invalid = {
            key: value
            for key, value in overrides.items()
            if not isinstance(value, int) or value < 0 or value > published[key]
        }
        if invalid:
            raise ValidationError(
                message="Tenant limits must be non-negative and no greater than platform limits",
                details={"limits": invalid},
            )
        return dict(overrides)

    @staticmethod
    def _read(
        definition: AgentDefinition,
        *,
        enabled: bool = False,
        overrides: dict[str, int] | None = None,
    ) -> AgentDefinitionRead:
        # Deliberately omit system_prompt/tool_policy/KB internals from this
        # projection. They remain server-side control-plane data.
        return AgentDefinitionRead(
            id=definition.id,
            slug=definition.slug,
            version=definition.version,
            role=definition.role,
            description=definition.description,
            capabilities=list(definition.capabilities or []),
            limits=dict(definition.limits or {}),
            enabled=enabled,
            tenant_limit_overrides=dict(overrides or {}),
            created_at=definition.created_at,
            updated_at=definition.updated_at,
        )

    async def list_for_tenant(self, organization_id: UUID, user_id: UUID) -> AgentDefinitionList:
        """List the published catalog with this tenant's enablement state."""
        await self._membership(organization_id, user_id)
        definitions = await definition_repo.list_published(self.db)
        bindings = {
            binding.definition_slug: binding for binding in await definition_repo.list_bindings(
                self.db, organization_id=organization_id
            )
        }
        items = []
        for definition in definitions:
            binding = bindings.get(definition.slug)
            items.append(
                self._read(
                    definition,
                    enabled=bool(binding and binding.enabled and binding.agent_definition_id == definition.id),
                    overrides=(binding.limit_overrides if binding and binding.agent_definition_id == definition.id else {}),
                )
            )
        return AgentDefinitionList(items=items, total=len(items))

    async def update(
        self,
        organization_id: UUID,
        definition_slug: str,
        data: AgentDefinitionUpdate,
        *,
        requester_id: UUID,
    ) -> AgentDefinitionRead:
        """Enable/disable or switch version without mutating platform content."""
        await self._require_admin(organization_id, requester_id)
        current_binding = await definition_repo.get_binding(
            self.db, organization_id=organization_id, definition_slug=definition_slug
        )
        version = data.version
        definition = await definition_repo.get_published(
            self.db, slug=definition_slug, version=version
        )
        if definition is None:
            raise NotFoundError(
                message="Published Agent Definition version not found",
                details={"slug": definition_slug, "version": version},
            )
        overrides = self._bounded_limits(definition, data.limit_overrides)
        if current_binding is None:
            binding = await definition_repo.create_binding(
                self.db,
                organization_id=organization_id,
                definition=definition,
                enabled=data.enabled,
                limit_overrides=overrides,
                enabled_by_user_id=requester_id,
            )
        else:
            binding = await definition_repo.update_binding(
                self.db,
                current_binding,
                definition=definition,
                enabled=data.enabled,
                limit_overrides=overrides,
                enabled_by_user_id=requester_id,
            )
        return self._read(definition, enabled=binding.enabled, overrides=binding.limit_overrides)

    async def get_runtime_definition(
        self, organization_id: UUID, definition_slug: str, user_id: UUID
    ) -> AgentDefinitionRuntime:
        """Resolve one enabled definition for a member's execution.

        This returns a plain control-plane DTO. The future AgentScope adapter
        is responsible for translating it through public extension points.
        """
        await self._membership(organization_id, user_id)
        binding = await definition_repo.get_binding(
            self.db, organization_id=organization_id, definition_slug=definition_slug
        )
        if not binding or not binding.enabled:
            raise NotFoundError(message="Agent Definition is not enabled for this tenant")
        definition = await self.db.get(AgentDefinition, binding.agent_definition_id)
        if not definition or not definition.is_published:
            raise NotFoundError(message="Published Agent Definition version not found")
        limits = dict(definition.limits or {})
        limits.update(binding.limit_overrides or {})
        return AgentDefinitionRuntime(
            slug=definition.slug,
            version=definition.version,
            role=definition.role,
            capabilities=list(definition.capabilities or []),
            limits=limits,
            knowledge_base_refs=list(definition.knowledge_base_refs or []),
            memory_scope=definition.memory_scope,
            system_prompt=definition.system_prompt,
            tool_policy=dict(definition.tool_policy or {}),
        )


__all__ = ["AgentDefinitionService"]
{%- else %}
"""AgentScope Agent Definition service — not configured."""
{%- endif %}
