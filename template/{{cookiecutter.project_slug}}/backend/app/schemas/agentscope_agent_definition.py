{%- if cookiecutter.use_agentscope and cookiecutter.enable_teams and cookiecutter.use_jwt %}
"""Safe public schemas for tenant Agent Definition enablement."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import ConfigDict, Field, field_validator

from app.schemas.base import BaseSchema, TimestampSchema


class AgentDefinitionRead(BaseSchema, TimestampSchema):
    """Public catalog projection; private prompt and policy are redacted."""

    id: UUID
    slug: str
    version: int
    role: str
    description: str | None = None
    capabilities: list[str]
    limits: dict[str, int]
    enabled: bool = False
    tenant_limit_overrides: dict[str, int] = Field(default_factory=dict)


class AgentDefinitionUpdate(BaseSchema):
    """Tenant-controlled enablement only; definition internals are forbidden."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool = True
    version: int | None = Field(default=None, ge=1)
    limit_overrides: dict[str, int] = Field(default_factory=dict)

    @field_validator("limit_overrides")
    @classmethod
    def valid_limits(cls, value: dict[str, int]) -> dict[str, int]:
        if any(not key or value < 0 for key, value in value.items()):
            raise ValueError("limit_overrides keys must be non-empty and values non-negative")
        return value


class AgentDefinitionList(BaseSchema):
    items: list[AgentDefinitionRead]
    total: int


class AgentDefinitionRuntime(BaseSchema):
    """Internal control-plane payload consumed by a runtime adapter."""

    slug: str
    version: int
    role: str
    capabilities: list[str]
    limits: dict[str, int]
    knowledge_base_refs: list[str]
    memory_scope: str
    # Kept out of API routes; callers must explicitly request this internal
    # payload and should not serialize it to clients.
    system_prompt: str
    tool_policy: dict[str, Any]


__all__ = [
    "AgentDefinitionList",
    "AgentDefinitionRead",
    "AgentDefinitionRuntime",
    "AgentDefinitionUpdate",
]
{%- else %}
"""AgentScope Agent Definition schemas — not configured."""
{%- endif %}
