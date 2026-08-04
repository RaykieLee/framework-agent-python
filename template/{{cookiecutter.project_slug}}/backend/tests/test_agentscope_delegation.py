{%- if cookiecutter.use_agentscope and cookiecutter.enable_teams and cookiecutter.use_jwt %}
"""Contract tests for non-escalating AgentScope worker authority."""

from collections.abc import Sequence

import pytest
from agentscope.permission import PermissionContext, PermissionMode

from app.schemas.agentscope_agent_definition import AgentDefinitionRuntime
from app.services.agentscope_delegation import (
    AgentScopeDelegationPolicy,
    CrossTenantConnection,
    DelegatedMCPGrant,
    NestedDelegationDenied,
    PersonalConnectionRecord,
    WorkerAuthorityDenied,
)
from app.services.agentscope_execution_team import (
    AgentScopeExecutionTeamCoordinator,
    ExecutionTeamContext,
)
from agentscope.app.message_bus import InMemoryMessageBus


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def _definition(slug: str = "researcher", *, policy: dict | None = None) -> AgentDefinitionRuntime:
    return AgentDefinitionRuntime(
        slug=slug,
        version=1,
        role="read-only researcher",
        capabilities=["chat"],
        limits={"max_turns": 5},
        knowledge_base_refs=[],
        memory_scope="tenant_user_agent",
        system_prompt="private definition prompt must not enter audit payload",
        tool_policy=policy or {},
    )


class FakeDefinitions:
    def __init__(self, definitions: Sequence[AgentDefinitionRuntime]) -> None:
        self.definitions = list(definitions)

    async def list_enabled(self, *, tenant_id: str, user_id: str) -> Sequence[AgentDefinitionRuntime]:
        assert (tenant_id, user_id) == ("tenant-a", "user-a")
        return self.definitions


class FakeConnections:
    def __init__(self, records: Sequence[PersonalConnectionRecord]) -> None:
        self.records = list(records)

    async def list_for_execution(self, *, tenant_id: str, user_id: str) -> Sequence[PersonalConnectionRecord]:
        return self.records


def _connection(*, tenant_id: str = "tenant-a", user_id: str = "user-a") -> PersonalConnectionRecord:
    return PersonalConnectionRecord(
        connection_id="connection-1",
        tenant_id=tenant_id,
        user_id=user_id,
        name="github",
        allowed_tools=("search_issues", "delete_repo"),
    )


async def _authority(policy: dict | None = None, records: Sequence[PersonalConnectionRecord] | None = None):
    definition = _definition(policy=policy)
    resolver = FakeDefinitions([definition])
    coordinator = AgentScopeExecutionTeamCoordinator(
        InMemoryMessageBus(), resolver
    )
    context = ExecutionTeamContext("tenant-a", "user-a", "conversation-a")
    team = await coordinator.create_team(context, leader_session_id="leader", requested_definition_slugs=["researcher"])
    worker_session = team.workers["researcher"].session_id
    policy_adapter = AgentScopeDelegationPolicy(
        resolver,
        FakeConnections(records or [_connection()]),
    )
    authority = await policy_adapter.issue(
        context,
        team,
        worker_session_id=worker_session,
        leader_permission_context=PermissionContext(mode=PermissionMode.ACCEPT_EDITS),
    )
    return authority


@pytest.mark.anyio
async def test_native_inheritance_flags_and_template_precedence_are_preserved() -> None:
    authority = await _authority(
        {
            "permission_mode": "explore",
            "override_leader_mode": True,
            "extend_leader_permission_rules": False,
            "extend_leader_working_directories": False,
            "deny_tools": ["Bash"],
            "ask_tools": ["MCP"],
        }
    )

    assert authority.template.override_leader_mode is True
    assert authority.template.extend_leader_permission_rules is False
    assert authority.template.extend_leader_working_directories is False
    assert authority.template.permission_context.mode == PermissionMode.EXPLORE
    assert authority.template.permission_context.deny_rules["Bash"][0].behavior.value == "deny"
    assert authority.template.permission_context.ask_rules["MCP"][0].behavior.value == "ask"


@pytest.mark.anyio
async def test_mcp_grants_are_tenant_bound_and_least_privilege() -> None:
    authority = await _authority(
        {
            "mcp_connections": ["github"],
            "mcp_tools": {"github": ["search_issues", "delete_repo"]},
            "deny_tools": ["delete_repo"],
        }
    )

    assert authority.mcp_grants == (
        DelegatedMCPGrant(
            connection_id="connection-1",
            name="github",
            allowed_tools=("search_issues",),
        ),
    )
    authority.check_tool("search_issues", connection_name="github")
    with pytest.raises(WorkerAuthorityDenied):
        authority.check_tool("delete_repo", connection_name="github")
    with pytest.raises(WorkerAuthorityDenied):
        authority.check_tool("search_issues", connection_name="other-tenant")


@pytest.mark.anyio
async def test_cross_tenant_connection_and_nested_team_are_rejected() -> None:
    with pytest.raises(CrossTenantConnection):
        await _authority(records=[_connection(tenant_id="tenant-b")])

    authority = await _authority()
    with pytest.raises(NestedDelegationDenied):
        authority.assert_can_create_team()
    assert authority.worker_can_create_team is False


@pytest.mark.anyio
async def test_leader_directory_outside_tenant_workspace_is_rejected() -> None:
    resolver = FakeDefinitions([_definition(policy={"workspace_root": "/srv/tenant-a"})])
    coordinator = AgentScopeExecutionTeamCoordinator(InMemoryMessageBus(), resolver)
    context = ExecutionTeamContext("tenant-a", "user-a", "conversation-a")
    team = await coordinator.create_team(context, leader_session_id="leader", requested_definition_slugs=["researcher"])
    worker_session = team.workers["researcher"].session_id
    leader_permissions = PermissionContext(
        working_directories={
            "/srv/other-tenant": {"path": "/srv/other-tenant", "source": "session"}
        }
    )
    with pytest.raises(WorkerAuthorityDenied):
        await AgentScopeDelegationPolicy(
            resolver,
            FakeConnections([_connection()]),
        ).issue(
            context,
            team,
            worker_session_id=worker_session,
            leader_permission_context=leader_permissions,
        )


@pytest.mark.anyio
async def test_worker_cannot_override_leader_with_bypass_mode() -> None:
    with pytest.raises(WorkerAuthorityDenied, match="BYPASS"):
        await _authority(
            {
                "permission_mode": "bypass",
                "override_leader_mode": True,
            }
        )


@pytest.mark.anyio
async def test_audit_payload_never_contains_private_prompt_or_credentials() -> None:
    authority = await _authority(
        {"mcp_connections": ["github"], "mcp_tools": {"github": ["search_issues"]}}
    )
    payload = authority.to_payload()
    serialized = repr(payload)
    assert "private definition prompt" not in serialized
    assert "Bearer" not in serialized
    assert "https://" not in serialized
    assert payload["mcp_grants"][0]["allowed_tools"] == ["search_issues"]
{%- else %}
"""AgentScope worker delegation tests are not configured."""
{%- endif %}
