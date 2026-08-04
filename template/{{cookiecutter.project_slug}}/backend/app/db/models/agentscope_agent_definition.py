{%- if cookiecutter.use_agentscope and cookiecutter.enable_teams and cookiecutter.use_jwt %}
"""Control-plane AgentScope Agent Definition models.

The platform catalog is immutable from tenant APIs.  A tenant stores only the
published definition version it enabled and bounded limit overrides; runtime
adapters receive resolved dictionaries rather than AgentScope-native objects.
"""

from __future__ import annotations

import uuid
from typing import Any

{%- if cookiecutter.use_sqlmodel %}
from sqlalchemy import Boolean, Column, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlmodel import Field, SQLModel

from app.db.base import TimestampMixin


class AgentDefinition(TimestampMixin, SQLModel, table=True):
    __tablename__ = "agent_definitions"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, sa_column=Column(PG_UUID(as_uuid=True), primary_key=True))
    slug: str = Field(sa_column=Column(String(64), nullable=False, index=True))
    version: int = Field(sa_column=Column(Integer, nullable=False))
    role: str = Field(sa_column=Column(String(128), nullable=False))
    description: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    capabilities: list[str] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    limits: dict[str, int] = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    system_prompt: str = Field(sa_column=Column(Text, nullable=False))
    tool_policy: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    knowledge_base_refs: list[str] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    memory_scope: str = Field(default="tenant_user_agent", sa_column=Column(String(64), nullable=False))
    is_published: bool = Field(default=True, sa_column=Column(Boolean, nullable=False, index=True))

    __table_args__ = (UniqueConstraint("slug", "version", name="uq_agent_definition_slug_version"),)


class TenantAgentDefinition(SQLModel, table=True):
    __tablename__ = "tenant_agent_definitions"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, sa_column=Column(PG_UUID(as_uuid=True), primary_key=True))
    organization_id: uuid.UUID = Field(sa_column=Column(PG_UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True))
    definition_slug: str = Field(sa_column=Column(String(64), nullable=False))
    agent_definition_id: uuid.UUID = Field(sa_column=Column(PG_UUID(as_uuid=True), ForeignKey("agent_definitions.id", ondelete="RESTRICT"), nullable=False))
    enabled: bool = Field(default=True, sa_column=Column(Boolean, nullable=False, index=True))
    limit_overrides: dict[str, int] = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    enabled_by_user_id: uuid.UUID | None = Field(default=None, sa_column=Column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True))

    __table_args__ = (UniqueConstraint("organization_id", "definition_slug", name="uq_tenant_agent_definition_slug"),)


__all__ = ["AgentDefinition", "TenantAgentDefinition"]

{%- else %}
from sqlalchemy import Boolean, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class AgentDefinition(Base, TimestampMixin):
    """Platform-published, versioned definition (never tenant-editable)."""

    __tablename__ = "agent_definitions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    role: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    capabilities: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    limits: Mapped[dict[str, int]] = mapped_column(JSON, nullable=False, default=dict)
    # Private control-plane fields: never included in public response schemas.
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    tool_policy: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    knowledge_base_refs: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    memory_scope: Mapped[str] = mapped_column(String(64), nullable=False, default="tenant_user_agent")
    is_published: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)

    __table_args__ = (UniqueConstraint("slug", "version", name="uq_agent_definition_slug_version"),)


class TenantAgentDefinition(Base, TimestampMixin):
    """One tenant's enablement pointer for a stable definition identity."""

    __tablename__ = "tenant_agent_definitions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Slug is the immutable tenant-facing identity; version changes update the
    # catalog foreign key while preserving this row and its audit identity.
    definition_slug: Mapped[str] = mapped_column(String(64), nullable=False)
    agent_definition_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agent_definitions.id", ondelete="RESTRICT"), nullable=False
    )
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    limit_overrides: Mapped[dict[str, int]] = mapped_column(JSON, nullable=False, default=dict)
    enabled_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    __table_args__ = (
        UniqueConstraint("organization_id", "definition_slug", name="uq_tenant_agent_definition_slug"),
    )


__all__ = ["AgentDefinition", "TenantAgentDefinition"]
{%- endif %}

{%- else %}
"""AgentScope Agent Definition models — not configured."""
{%- endif %}
