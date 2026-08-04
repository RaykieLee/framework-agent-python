{%- if cookiecutter.use_agentscope and cookiecutter.enable_teams and cookiecutter.use_jwt %}
"""Tenant Agent Definition enablement API (control plane only)."""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, status

from app.api.deps import CurrentUser, DBSession
from app.schemas.agentscope_agent_definition import AgentDefinitionList, AgentDefinitionRead, AgentDefinitionUpdate
from app.services.agentscope_agent_definition import AgentDefinitionService

router = APIRouter()


def _service(db: DBSession) -> AgentDefinitionService:
    return AgentDefinitionService(db)


@router.get("/{organization_id}/agent-definitions", response_model=AgentDefinitionList)
async def list_agent_definitions(
    organization_id: UUID,
    db: DBSession,
    user: CurrentUser,
) -> AgentDefinitionList:
    """List published definitions and this tenant's enablement state."""
    return await _service(db).list_for_tenant(organization_id, user.id)


@router.put(
    "/{organization_id}/agent-definitions/{definition_slug}",
    response_model=AgentDefinitionRead,
    status_code=status.HTTP_200_OK,
)
async def update_agent_definition(
    organization_id: UUID,
    definition_slug: str,
    data: AgentDefinitionUpdate,
    db: DBSession,
    user: CurrentUser,
) -> Any:
    """Enable, disable, or select a published version (Owner/Admin only)."""
    return await _service(db).update(
        organization_id,
        definition_slug,
        data,
        requester_id=user.id,
    )


{%- else %}
"""Agent Definition routes — not configured."""
{%- endif %}
