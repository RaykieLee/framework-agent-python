{%- if cookiecutter.use_agentscope and cookiecutter.use_jwt %}
"""Focused tests for generated AgentScope control-plane wiring."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from agentscope.message import Msg, TextBlock

from app.services.agent_session import AgentSession
from app.services.agentscope_runtime import (
    AgentScopeRuntimeWiring,
    AgentScopeTenantContext,
    get_agentscope_runtime,
)


def test_default_runtime_wiring_has_durable_store_and_cleanup_guard() -> None:
    runtime = get_agentscope_runtime()
    assert runtime.durable_store_factory() is not None
    assert runtime.member_exit_cleanup is not None
    assert runtime.tenant_purge_service is not None
    assert runtime.team_run_coordinator is not None
    assert runtime.resource_factory is not None


@pytest.mark.anyio
async def test_default_resources_are_tenant_bound() -> None:
    runtime = get_agentscope_runtime()
    resources = await runtime.execution_resources(AgentScopeTenantContext("tenant-a", "user-a", "member", False))
    assert resources.knowledge_base.tenant_id == "tenant-a"
    assert resources.memory_middleware.tenant_id == "tenant-a"
    assert resources.delegation_policy.tenant_id == "tenant-a"
    assert resources.personal_connections[0].tenant_id == "tenant-a"


@pytest.mark.anyio
async def test_team_control_frame_uses_server_tenant_context() -> None:
    websocket = MagicMock()
    websocket.send_json = AsyncMock()
    seen: dict[str, object] = {}

    async def handle(context: AgentScopeTenantContext, frame: dict[str, object]) -> dict[str, object]:
        seen.update({"tenant_id": context.tenant_id, "frame_tenant_id": frame.get("active_tenant_id")})
        return {"run_id": "run-a", "tenant_id": context.tenant_id}

    runtime = AgentScopeRuntimeWiring(
        durable_store_factory=lambda: get_agentscope_runtime().durable_store_factory(),
        team_frame_handler=handle,
    )
    session = AgentSession(
        websocket,
        tenant_context=AgentScopeTenantContext("tenant-a", "user-a", "owner", False),
        runtime_wiring=runtime,
    )
    await session.handle_frame({"type": "team_start", "active_tenant_id": "tenant-b"})

    assert seen == {"tenant_id": "tenant-a", "frame_tenant_id": "tenant-b"}
    message = websocket.send_json.await_args.args[0]
    assert message["type"] == "team_run"
    assert message["data"]["tenant_id"] == "tenant-a"


@pytest.mark.anyio
async def test_session_ignores_forged_frame_tenant_fields() -> None:
    websocket = MagicMock()
    websocket.send_json = AsyncMock()

    class FakeAssistant:
        model_name = "test-model"

        async def stream(self, _message: str, *, continuation=None):
            del continuation
            yield Msg(name="assistant", role="assistant", content=[TextBlock(text="ok")])

    context = AgentScopeTenantContext("tenant-a", "user-a", "member", False)
    session = AgentSession(
        websocket,
        user=SimpleNamespace(id="user-a"),
        assistant=FakeAssistant(),
        tenant_context=context,
    )
    with patch(
        "app.services.agent_session.persist_user_turn",
        new=AsyncMock(return_value=("conversation-a", True, "tenant-a")),
    ), patch(
        "app.services.agent_session.persist_assistant_turn",
        new=AsyncMock(return_value="message-a"),
    ):
        await session.process_message(
            {
                "message": "hello",
                "active_tenant_id": "tenant-b",
                "conversation_tenant_id": "tenant-b",
                "active_tenant_role": "owner",
            }
        )

    complete = [call.args[0] for call in websocket.send_json.await_args_list if call.args[0]["type"] == "complete"]
    assert complete and complete[-1]["data"]["content"] == "ok"
{%- else %}
"""AgentScope runtime wiring is not configured."""
{%- endif %}
