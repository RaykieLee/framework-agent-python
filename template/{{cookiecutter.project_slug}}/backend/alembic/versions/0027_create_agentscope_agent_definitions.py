{%- if cookiecutter.use_agentscope and cookiecutter.enable_teams and cookiecutter.use_jwt %}
"""Create the platform Agent Definition catalog and tenant bindings."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0027_agent_definitions"
down_revision = "0025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "agent_definitions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("slug", sa.String(64), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(128), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("capabilities", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("limits", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("system_prompt", sa.Text(), nullable=False),
        sa.Column("tool_policy", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("knowledge_base_refs", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("memory_scope", sa.String(64), nullable=False, server_default="tenant_user_agent"),
        sa.Column("is_published", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug", "version", name="uq_agent_definition_slug_version"),
    )
    op.create_index("ix_agent_definitions_slug", "agent_definitions", ["slug"])
    op.create_index("ix_agent_definitions_is_published", "agent_definitions", ["is_published"])

    op.create_table(
        "tenant_agent_definitions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("definition_slug", sa.String(64), nullable=False),
        sa.Column("agent_definition_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("limit_overrides", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("enabled_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["agent_definition_id"], ["agent_definitions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["enabled_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "definition_slug", name="uq_tenant_agent_definition_slug"),
    )
    op.create_index("ix_tenant_agent_definitions_org", "tenant_agent_definitions", ["organization_id"])
    op.create_index("ix_tenant_agent_definitions_enabled", "tenant_agent_definitions", ["enabled"])

    # A small curated catalog is platform-owned; tenants only select versions.
    op.bulk_insert(
        sa.table(
            "agent_definitions",
            sa.column("id", postgresql.UUID(as_uuid=True)),
            sa.column("slug", sa.String),
            sa.column("version", sa.Integer),
            sa.column("role", sa.String),
            sa.column("description", sa.Text),
            sa.column("capabilities", postgresql.JSONB),
            sa.column("limits", postgresql.JSONB),
            sa.column("system_prompt", sa.Text),
            sa.column("tool_policy", postgresql.JSONB),
            sa.column("knowledge_base_refs", postgresql.JSONB),
            sa.column("memory_scope", sa.String),
            sa.column("is_published", sa.Boolean),
        ),
        [
            {
                "id": "4a3c9e0c-1a06-4ed9-a7f1-4d8b5ea4e701",
                "slug": "general-assistant",
                "version": 1,
                "role": "General assistant",
                "description": "A safe general-purpose tenant assistant.",
                "capabilities": ["chat"],
                "limits": {"max_turns": 20, "max_tokens": 8192},
                "system_prompt": "You are the platform general assistant.",
                "tool_policy": {"allowed": []},
                "knowledge_base_refs": [],
                "memory_scope": "tenant_user_agent",
                "is_published": True,
            },
            {
                "id": "bb6e8d8d-6cf1-4da9-8f58-6e638bc95502",
                "slug": "research-assistant",
                "version": 1,
                "role": "Research assistant",
                "description": "Retrieval-focused assistant for governed sources.",
                "capabilities": ["chat", "retrieval"],
                "limits": {"max_turns": 30, "max_tokens": 12288},
                "system_prompt": "You are the platform research assistant.",
                "tool_policy": {"allowed": ["control_plane_retrieval"]},
                "knowledge_base_refs": ["tenant-authorized"],
                "memory_scope": "tenant_user_agent",
                "is_published": True,
            },
        ],
    )


def downgrade() -> None:
    op.drop_table("tenant_agent_definitions")
    op.drop_index("ix_agent_definitions_is_published", table_name="agent_definitions")
    op.drop_index("ix_agent_definitions_slug", table_name="agent_definitions")
    op.drop_table("agent_definitions")

{%- else %}
"""Agent Definition migration — skipped (AgentScope teams/JWT disabled)."""

revision = "0027_agent_definitions"
down_revision = "0025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
{%- endif %}
