{%- if cookiecutter.use_agentscope and cookiecutter.enable_teams and cookiecutter.use_jwt %}
"""Contract tests for the conversation-scoped Execution Team seam."""

from collections.abc import Sequence
from uuid import uuid4

import pytest
from agentscope.app.message_bus import InMemoryMessageBus

from app.core.exceptions import AuthorizationError, NotFoundError
from app.schemas.agentscope_agent_definition import AgentDefinitionRuntime
from app.services.agentscope_execution_team import (
    AgentDefinitionUnavailable,
    AgentScopeExecutionTeamCoordinator,
    ExecutionTeamContext,
    NestedTeamNotAllowed,
    NotTeamLeader,
    WorkerLimitExceeded,
)


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


class FakeDefinitionResolver:
    def __init__(self, definitions: Sequence[AgentDefinitionRuntime]) -> None:
        self.definitions = list(definitions)

    async def list_enabled(self, *, tenant_id: str, user_id: str) -> Sequence[AgentDefinitionRuntime]:
        assert tenant_id == "tenant-a"
        assert user_id == "user-a"
        return self.definitions


def _definition(slug: str, *, version: int = 1) -> AgentDefinitionRuntime:
    return AgentDefinitionRuntime(
        slug=slug,
        version=version,
        role=f"{slug} worker",
        capabilities=["chat"],
        limits={"max_turns": 5},
        knowledge_base_refs=[],
        memory_scope="tenant_user_agent",
        system_prompt=f"private prompt for {slug}",
        tool_policy={},
    )


def _context(**overrides: str) -> ExecutionTeamContext:
    return ExecutionTeamContext(
        tenant_id=overrides.get("tenant_id", "tenant-a"),
        user_id=overrides.get("user_id", "user-a"),
        conversation_id=overrides.get("conversation_id", "conversation-a"),
        active_tenant_role=overrides.get("active_tenant_role", "member"),
    )


def _coordinator(*slugs: str) -> AgentScopeExecutionTeamCoordinator:
    return AgentScopeExecutionTeamCoordinator(
        InMemoryMessageBus(),
        FakeDefinitionResolver([_definition(slug) for slug in slugs]),
    )


@pytest.mark.anyio
async def test_leader_selects_enabled_definitions_and_emits_native_roster() -> None:
    coordinator = _coordinator("research", "writer", "reviewer")
    state = await coordinator.create_team(
        _context(),
        leader_session_id="leader-session",
        requested_definition_slugs=["writer", "reviewer"],
    )

    assert list(state.workers) == ["writer", "reviewer"]
    assert state.native_record.user_id == "user-a"
    assert state.native_record.session_id == "leader-session"
    assert [member.agent_id for member in state.native_record.data.members] == ["writer", "reviewer"]
    events = await coordinator.reconnect(_context(), state.team_id)
    assert events.events[0]["type"] == "team_created"
    assert events.events[0]["tenant_id"] == "tenant-a"


@pytest.mark.anyio
async def test_worker_limit_and_unenabled_definition_are_rejected() -> None:
    slugs = [f"worker-{index}" for index in range(7)]
    coordinator = _coordinator(*slugs)
    with pytest.raises(WorkerLimitExceeded):
        await coordinator.create_team(
            _context(),
            leader_session_id="leader-session",
            requested_definition_slugs=slugs,
        )

    coordinator = _coordinator("writer")
    with pytest.raises(AgentDefinitionUnavailable):
        await coordinator.create_team(
            _context(), leader_session_id="leader-session", requested_definition_slugs=["missing"]
        )


@pytest.mark.anyio
async def test_only_leader_adds_workers_and_workers_cannot_nest() -> None:
    coordinator = _coordinator("writer", "reviewer")
    state = await coordinator.create_team(
        _context(), leader_session_id="leader-session", requested_definition_slugs=["writer"]
    )
    worker_session = state.workers["writer"].session_id

    with pytest.raises(NotTeamLeader):
        await coordinator.add_worker(
            _context(), state.team_id, actor_session_id=worker_session, definition_slug="reviewer"
        )
    state = await coordinator.add_worker(
        _context(), state.team_id, actor_session_id="leader-session", definition_slug="reviewer"
    )
    assert list(state.workers) == ["writer", "reviewer"]
    with pytest.raises(NestedTeamNotAllowed):
        await coordinator.create_team(
            _context(),
            leader_session_id=worker_session,
            requesting_session_id=worker_session,
            parent_team_id=state.team_id,
            requested_definition_slugs=["reviewer"],
        )


@pytest.mark.anyio
async def test_direct_and_broadcast_messages_use_member_inboxes() -> None:
    coordinator = _coordinator("writer", "reviewer")
    state = await coordinator.create_team(
        _context(), leader_session_id="leader-session", requested_definition_slugs=["writer", "reviewer"]
    )
    writer_session = state.workers["writer"].session_id
    reviewer_session = state.workers["reviewer"].session_id

    await coordinator.direct_message(
        _context(), state.team_id, sender_session_id="leader-session", recipient="writer", content="draft"
    )
    assert (await coordinator.drain_inbox(_context(), state.team_id, recipient_session_id=writer_session))[0][
        "content"
    ] == "draft"
    assert await coordinator.broadcast(
        _context(), state.team_id, sender_session_id="leader-session", content="standup"
    ) == 2
    assert (await coordinator.drain_inbox(_context(), state.team_id, recipient_session_id=writer_session))[0][
        "content"
    ] == "standup"
    assert (await coordinator.drain_inbox(_context(), state.team_id, recipient_session_id=reviewer_session))[0][
        "content"
    ] == "standup"


@pytest.mark.anyio
async def test_worker_completion_and_failure_are_isolated_and_replayed_on_reconnect() -> None:
    coordinator = _coordinator("writer", "reviewer")
    state = await coordinator.create_team(
        _context(), leader_session_id="leader-session", requested_definition_slugs=["writer", "reviewer"]
    )
    writer_session = state.workers["writer"].session_id
    reviewer_session = state.workers["reviewer"].session_id

    await coordinator.worker_completed(
        _context(), state.team_id, worker_session_id=writer_session, result={"text": "done"}
    )
    state = await coordinator.worker_failed(
        _context(), state.team_id, worker_session_id=reviewer_session, error="timeout"
    )
    assert state.status == "failed"
    assert state.workers["writer"].status == "completed"
    assert state.workers["reviewer"].status == "failed"
    replay = await coordinator.reconnect(_context(), state.team_id)
    assert [event["type"] for event in replay.events] == [
        "team_created",
        "worker_completed",
        "worker_failed",
    ]


@pytest.mark.anyio
async def test_active_tenant_and_viewer_isolation_are_enforced() -> None:
    coordinator = _coordinator("writer")
    state = await coordinator.create_team(
        _context(), leader_session_id="leader-session", requested_definition_slugs=["writer"]
    )
    with pytest.raises(AuthorizationError):
        await coordinator.direct_message(
            _context(tenant_id="tenant-b"),
            state.team_id,
            sender_session_id="leader-session",
            recipient="writer",
            content="leak",
        )
    with pytest.raises(AuthorizationError):
        ExecutionTeamContext(
            tenant_id="tenant-a",
            user_id="viewer",
            conversation_id="conversation-a",
            active_tenant_role="viewer",
        )


@pytest.mark.integration
@pytest.mark.anyio
async def test_redis_message_bus_boundary_is_explicit() -> None:
    """Run against Redis only when the generated integration stack is available."""
    import os

    redis_url = os.getenv("AGENTSCOPE_INTEGRATION_REDIS_URL")
    if not redis_url:
        pytest.skip("set AGENTSCOPE_INTEGRATION_REDIS_URL for Redis MessageBus integration")
    from agentscope.app.message_bus import RedisMessageBus

    async with RedisMessageBus(url=redis_url) as bus:
        coordinator = AgentScopeExecutionTeamCoordinator(
            bus, FakeDefinitionResolver([_definition("writer")])
        )
        state = await coordinator.create_team(
            _context(conversation_id=f"redis-{uuid4().hex}"),
            leader_session_id="leader-session",
            requested_definition_slugs=["writer"],
        )
        await coordinator.direct_message(
            state.context,
            state.team_id,
            sender_session_id="leader-session",
            recipient="writer",
            content="redis",
        )
        assert (await coordinator.drain_inbox(
            state.context, state.team_id, recipient_session_id=state.workers["writer"].session_id
        ))[0]["content"] == "redis"
{%- else %}
"""Execution Team tests are not configured."""
{%- endif %}
