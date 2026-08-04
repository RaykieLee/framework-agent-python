{%- if cookiecutter.use_agentscope %}
"""Unit tests for the AgentScope durable-session seam."""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest
from agentscope.message import Msg, TextBlock

from app.services.agentscope_durable_session import (
    AgentScopeDurableSession,
    InMemoryDurableSessionStore,
    RequestCancelled,
    event_key,
    mapping_key,
    request_key,
)


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.mark.anyio
async def test_mapping_survives_new_process_and_is_tenant_prefixed() -> None:
    store = InMemoryDurableSessionStore()
    first = AgentScopeDurableSession(store, tenant_id="tenant-a", conversation_id="conv-1")
    second = AgentScopeDurableSession(store, tenant_id="tenant-a", conversation_id="conv-1")

    first_ref = await first.open()
    second_ref = await second.open()

    assert first_ref == second_ref
    assert mapping_key("tenant-a", "conv-1").startswith("agentscope:tenant:tenant-a-")
    assert request_key(first_ref) != request_key(first_ref.__class__("tenant-b", "conv-1", first_ref.agent_session_id))
    assert event_key(first_ref).startswith("agentscope:")


@pytest.mark.anyio
async def test_duplicate_request_is_idempotent_for_runner_and_charge() -> None:
    store = InMemoryDurableSessionStore()
    session = AgentScopeDurableSession(store, tenant_id="tenant-a", conversation_id="conv-1")
    calls = 0
    charges = 0

    async def runner(_token):
        nonlocal calls
        calls += 1
        await asyncio.sleep(0)
        return "answer"

    async def charge(_request_id: str) -> None:
        nonlocal charges
        charges += 1

    first = await session.execute("req-1", runner, charge=charge)
    replay = await session.execute("req-1", runner, charge=charge)

    assert first == replay
    assert calls == 1
    assert charges == 1


@pytest.mark.anyio
async def test_lock_contention_runs_one_request_across_workers() -> None:
    store = InMemoryDurableSessionStore()
    one = AgentScopeDurableSession(store, tenant_id="tenant-a", conversation_id="conv-1")
    two = AgentScopeDurableSession(store, tenant_id="tenant-a", conversation_id="conv-1")
    calls = 0

    async def runner(_token):
        nonlocal calls
        calls += 1
        await asyncio.sleep(0.01)
        return "answer"

    results = await asyncio.gather(
        one.execute("req-1", runner),
        two.execute("req-1", runner),
    )

    assert results[0] == results[1]
    assert calls == 1


@pytest.mark.anyio
async def test_replay_claims_buffered_events_once_after_reconnect() -> None:
    store = InMemoryDurableSessionStore()
    first = AgentScopeDurableSession(store, tenant_id="tenant-a", conversation_id="conv-1")
    await first.emit("req-1", "text_delta", {"delta": "hi"})

    second = AgentScopeDurableSession(store, tenant_id="tenant-a", conversation_id="conv-1")
    replay = await second.replay()
    again = await second.replay()

    assert [event.name for event in replay] == ["text_delta"]
    assert again == []


@pytest.mark.anyio
async def test_cancellation_flag_reaches_running_request() -> None:
    store = InMemoryDurableSessionStore()
    session = AgentScopeDurableSession(store, tenant_id="tenant-a", conversation_id="conv-1")
    started = asyncio.Event()

    async def runner(token):
        started.set()
        while True:
            await token.raise_if_cancelled()
            await asyncio.sleep(0.001)

    task = asyncio.create_task(session.execute("req-1", runner))
    await started.wait()
    await session.cancel("req-1")

    with pytest.raises(RequestCancelled):
        await task


@pytest.mark.anyio
async def test_agent_session_uses_durable_request_boundary_once() -> None:
    from app.services.agent_session import AgentSession

    class Socket:
        def __init__(self) -> None:
            self.events: list[dict[str, object]] = []

        async def send_json(self, event: dict[str, object]) -> None:
            self.events.append(event)

    class Assistant:
        model_name = "test-model"

        def __init__(self) -> None:
            self.calls = 0

        async def stream(self, _message: str, *, continuation=None):
            self.calls += 1
            yield Msg(name="assistant", role="assistant", content=[TextBlock(text="answer")])

    socket = Socket()
    assistant = Assistant()
    durable = AgentScopeDurableSession(
        InMemoryDurableSessionStore(), tenant_id="tenant-a", conversation_id="conv-1"
    )
    session = AgentSession(socket, assistant=assistant, durable_session=durable)

    with (
        patch(
            "app.services.agent_session.persist_user_turn",
            new=AsyncMock(return_value=("conv-1", False, None)),
        ),
        patch(
            "app.services.agent_session.persist_assistant_turn",
            new=AsyncMock(return_value="message-1"),
        ),
    ):
        await session.process_message({"message": "hi", "request_id": "req-1"})
        await session.process_message({"message": "hi", "request_id": "req-1"})

    assert assistant.calls == 1
    assert any(event.get("data", {}).get("replayed") is True for event in socket.events)
{%- else %}
"""AgentScope durable-session tests are not configured."""
{%- endif %}
