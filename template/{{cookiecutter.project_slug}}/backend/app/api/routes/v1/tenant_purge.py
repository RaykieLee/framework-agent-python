{%- if cookiecutter.use_agentscope and cookiecutter.enable_teams and cookiecutter.use_jwt %}
"""Owner-confirmed Tenant Purge API.

The route only queues work and exposes redaction-safe status.  A deployment
must call ``configure_tenant_purge_service`` at boot with its durable SQL,
Redis, vector, memory, workspace, connection, audit, and queue adapters.
"""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, status

from app.api.deps import CurrentUser, OrganizationSvc
from app.core.exceptions import AuthorizationError, BadRequestError, NotFoundError
from app.db.models.organization import OrgRole
from app.schemas.agentscope_tenant_purge import TenantPurgeCreate, TenantPurgeStatus
from app.services.agentscope_tenant_purge import (
    TenantPurgeNotFound,
    TenantPurgeRequest,
    TenantPurgeService,
    get_configured_tenant_purge_service,
)

router = APIRouter()


def _service() -> TenantPurgeService:
    return get_configured_tenant_purge_service()


async def _require_owner_or_admin(
    org_id: UUID, user: Any, organization_service: OrganizationSvc
) -> Any:
    org, membership = await organization_service.get_for_user(org_id, user.id)
    if org.is_personal:
        raise BadRequestError(message="Personal organization cannot be purged")
    if membership.role not in (OrgRole.OWNER.value, OrgRole.ADMIN.value):
        raise AuthorizationError(message="Only the Owner or Admin can purge the organization")
    return org


@router.post(
    "/{org_id}/purge",
    response_model=TenantPurgeStatus,
    status_code=status.HTTP_202_ACCEPTED,
)
async def request_tenant_purge(
    org_id: UUID,
    data: TenantPurgeCreate,
    organization_service: OrganizationSvc,
    user: CurrentUser,
) -> TenantPurgeStatus:
    """Queue an asynchronous purge after Owner RBAC and exact confirmation."""
    org = await _require_owner_or_admin(org_id, user, organization_service)
    request = TenantPurgeRequest(
        tenant_id=str(org.id),
        actor_user_id=str(user.id),
        request_id=data.request_id,
        confirmation=data.confirmation,
    )
    service = _service()
    job = await service.request(request)
    return TenantPurgeStatus.from_job(job)


@router.get(
    "/{org_id}/purge/{job_id}",
    response_model=TenantPurgeStatus,
)
async def get_tenant_purge_status(
    org_id: UUID,
    job_id: str,
    organization_service: OrganizationSvc,
    user: CurrentUser,
) -> TenantPurgeStatus:
    """Return status only for a job whose immutable Tenant matches the path."""
    await _require_owner_or_admin(org_id, user, organization_service)
    try:
        job = await _service().status(tenant_id=str(org_id), job_id=job_id)
    except TenantPurgeNotFound as exc:
        raise NotFoundError(message="Tenant purge job not found") from exc
    return TenantPurgeStatus.from_job(job)


__all__ = ["router"]
{%- else %}
"""Tenant Purge routes — not configured."""
{%- endif %}
