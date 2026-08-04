{%- if cookiecutter.use_agentscope %}
"""Unit tests for the AgentScope-to-product chat seam."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from agentscope.event import ReplyEndEvent, TextBlockDeltaEvent
from agentscope.message import Msg, TextBlock

from app.services.agent_session import (
    ActiveTenantError,
    AgentSession,
    authorize_execution,
    event_to_wire,
)


class FakeAssistant:
    model_name = "test-model"

    def __init__(self, events):
        self.events = events

    async def stream(self, _message, *, continuation=None):
        del continuation
        for event in self.events:
            yield event


def _reply(text: str) -> Msg:
    return Msg(name="assistant", role="assistant", content=[TextBlock(text=text)])


def test_event_adapter_preserves_text_delta_and_reply_identity():
    event = TextBlockDeltaEvent(reply_id="reply-1", block_id="block-1", delta="hello")
    assert event_to_wire(event) == (
        "text_delta",
        {"reply_id": "reply-1", "delta": "hello"},
    )


def test_event_adapter_maps_model_terminal_event():
    event = ReplyEndEvent(session_id="session-1", reply_id="reply-1")
    event_type, payload = event_to_wire(event)
    assert event_type == "agent_end"
    assert payload["reply_id"] == "reply-1"


def test_viewer_and_cross_tenant_execution_are_rejected():
    with pytest.raises(ActiveTenantError, match="viewers"):
        authorize_execution(active_tenant_role="viewer")
    with pytest.raises(ActiveTenantError, match="active tenant"):
        authorize_execution(active_tenant_id="tenant-a", conversation_tenant_id="tenant-b")


@pytest.mark.anyio
async def test_session_streams_text_and_completes():
    websocket = MagicMock()
    websocket.send_json = AsyncMock()
    events = [
        TextBlockDeltaEvent(reply_id="reply-1", block_id="block-1", delta="hello"),
        _reply("hello"),
    ]
    assistant = FakeAssistant(events)
    session = AgentSession(websocket, assistant=assistant)
    with (
        patch(
            "app.services.agent_session.persist_user_turn",
            new=AsyncMock(return_value=("conversation-1", True, "tenant-1")),
        ),
        patch("app.services.agent_session.persist_assistant_turn", new=AsyncMock(return_value="message-1")),
    ):
        await session.process_message({"message": "hi"})

    sent = [call.args[0] for call in websocket.send_json.await_args_list]
    assert {item["type"] for item in sent} >= {"user_prompt", "text_delta", "message_saved", "complete"}
    complete = next(item for item in sent if item["type"] == "complete")
    assert complete["data"]["content"] == "hello"
{%- endif %}
