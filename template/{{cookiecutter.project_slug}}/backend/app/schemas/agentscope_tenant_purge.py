{%- if cookiecutter.use_agentscope and cookiecutter.enable_teams and cookiecutter.use_jwt %}
"""Product-safe request and status schemas for Tenant Purge."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import Field

from app.schemas.base import BaseSchema


class TenantPurgeCreate(BaseSchema):
    """Explicit confirmation required before an irreversible purge is queued."""

    confirmation: str = Field(
        min_length=1,
        max_length=256,
        description="Type exactly PURGE {tenant_id} to confirm deletion.",
    )
    request_id: str = Field(min_length=1, max_length=128)


class TenantPurgeStatus(BaseSchema):
    """Redaction-safe status; adapter errors and credentials are never exposed."""

    job_id: str
    tenant_id: str
    status: str
    completed_stores: list[str]
    failed_stores: list[str]
    attempts: int
    can_retry: bool
    created_at: datetime
    updated_at: datetime
    finished_at: datetime | None = None

    @classmethod
    def from_job(cls, job: Any) -> "TenantPurgeStatus":
        return cls(**job.public())


__all__ = ["TenantPurgeCreate", "TenantPurgeStatus"]
{%- else %}
"""AgentScope Tenant purge schemas are not configured."""
{%- endif %}
