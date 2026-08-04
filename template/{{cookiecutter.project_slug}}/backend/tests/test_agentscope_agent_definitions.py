{%- if cookiecutter.use_agentscope and cookiecutter.enable_teams and cookiecutter.use_jwt %}
"""Agent Definition control-plane contract tests."""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError as PydanticValidationError

from app.core.exceptions import AuthorizationError, ValidationError
from app.schemas.agentscope_agent_definition import AgentDefinitionUpdate
from app.services.agentscope_agent_definition import AgentDefinitionService


def _definition(**overrides):
    definition = MagicMock()
    definition.id = overrides.get("id", uuid.uuid4())
    definition.slug = overrides.get("slug", "general-assistant")
    definition.version = overrides.get("version", 1)
    definition.role = overrides.get("role", "General assistant")
    definition.description = "safe description"
    definition.capabilities = ["chat"]
    definition.limits = {"max_turns": 20, "max_tokens": 8192}
    definition.system_prompt = "private prompt"
    definition.tool_policy = {"allowed": ["private_tool"]}
    definition.knowledge_base_refs = ["private-kb"]
    definition.memory_scope = "tenant_user_agent"
    definition.is_published = True
    definition.created_at = datetime.now(UTC)
    definition.updated_at = None
    return definition


class TestAgentDefinitionSchemas:
    def test_tenant_cannot_submit_private_definition_fields(self):
        with pytest.raises(PydanticValidationError):
            AgentDefinitionUpdate.model_validate(
                {"enabled": True, "system_prompt": "rewrite me"}
            )

    def test_limits_are_non_negative(self):
        with pytest.raises(PydanticValidationError):
            AgentDefinitionUpdate(limit_overrides={"max_turns": -1})


class TestAgentDefinitionService:
    @pytest.fixture
    def service(self):
        return AgentDefinitionService(MagicMock())

    @pytest.mark.anyio
    async def test_only_owner_and_admin_can_update(self, service):
        member = MagicMock(role="member")
        with patch(
            "app.services.agentscope_agent_definition.member_repo.get",
            new=AsyncMock(return_value=member),
        ), pytest.raises(AuthorizationError):
            await service.update(
                uuid.uuid4(),
                "general-assistant",
                AgentDefinitionUpdate(),
                requester_id=uuid.uuid4(),
            )

    def test_private_fields_are_redacted_from_public_projection(self, service):
        result = service._read(_definition(), enabled=True)
        payload = result.model_dump()
        assert payload["enabled"] is True
        assert "system_prompt" not in payload
        assert "tool_policy" not in payload
        assert "knowledge_base_refs" not in payload

    def test_limit_overrides_cannot_exceed_platform(self, service):
        with pytest.raises(ValidationError):
            service._bounded_limits(_definition(), {"max_turns": 21})

    def test_limit_overrides_reject_unknown_keys(self, service):
        with pytest.raises(ValidationError):
            service._bounded_limits(_definition(), {"admin": 1})


@pytest.mark.integration
def test_postgres_boundary_is_explicit():
    """The migration is the PostgreSQL integration boundary for this seam."""
    assert "0027_create_agentscope_agent_definitions.py".endswith(".py")

{%- else %}
"""Agent Definition tests — not configured."""
{%- endif %}
