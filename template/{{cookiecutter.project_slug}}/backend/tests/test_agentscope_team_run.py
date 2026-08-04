{%- if cookiecutter.use_agentscope and cookiecutter.enable_teams and cookiecutter.use_jwt and cookiecutter.enable_billing and cookiecutter.enable_credits_system %}
"""Unit and explicit infrastructure-boundary tests for Team Run accounting."""

from __future__ import annotations

import os
import pytest

from app.services.agentscope_team_run import (
    AgentScopeTeamRunService,
    InMemoryTeamRunStore,
    InvalidUsage,
    TeamMemberStatus,
    TeamRunContext,
    TeamRunNotFound,
    TeamRunStatus,
    TeamRunStopReason,
    TeamRunTerminalError,
    TeamRunOwnershipError,
    RedisTeamRunCancellation,
    UsageDelta,
)


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def _context(**overrides: str) -> TeamRunContext:
    return TeamRunContext(
        tenant_id=overrides.get("tenant_id", "tenant-a"),
        user_id=overrides.get("user_id", "user-a"),
        conversation_id=overrides.get("conversation_id", "conversation-a"),
        team_id=overrides.get("team_id", "team-a"),
    )


class CancellationRecorder:
    def __init__(self) -> None:
        self.calls: list[tuple[str, TeamRunStopReason, str]] = []

    async def cancel(self, *, session_id: str, reason: TeamRunStopReason, tenant_id: str) -> None:
        self.calls.append((session_id, reason, tenant_id))


async def _started(
    *,
    budget: int | None = None,
    tenant_budget: int | None = None,
    cancellation: CancellationRecorder | None = None,
) -> tuple[AgentScopeTeamRunService, TeamRunContext, CancellationRecorder]:
    recorder = cancellation or CancellationRecorder()
    service = AgentScopeTeamRunService(InMemoryTeamRunStore(), cancellation=recorder)
    context = _context()
    await service.start(
        context,
        run_id="run-a",
        leader_session_id="leader",
        worker_session_ids=["worker-1", "worker-2"],
        run_budget_credits=budget,
        tenant_budget_credits=tenant_budget,
    )
    return service, context, recorder


@pytest.mark.anyio
async def test_usage_is_one_tenant_run_with_per_worker_diagnostics() -> None:
    service, context, _ = await _started()

    await service.record_usage(
        context,
        "run-a",
        UsageDelta("leader", "model", credits=5, input_tokens=10, output_tokens=3, event_id="m1"),
    )
    state = await service.record_usage(
        context,
        "run-a",
        UsageDelta("worker-1", "retrieval", credits=2, input_tokens=4, event_id="r1"),
    )

    assert state.context == _context()
    assert state.total_credits == 7
    assert state.total_input_tokens == 14
    assert state.usage["leader"].by_kind == {"model": 5}
    assert state.usage["worker-1"].by_kind == {"retrieval": 2}
    assert (await service.events(context, "run-a"))[-1].type == "usage_recorded"


@pytest.mark.anyio
async def test_duplicate_usage_event_is_not_double_charged() -> None:
    service, context, _ = await _started()
    delta = UsageDelta("worker-1", "tool", credits=9, event_id="same-event")

    first = await service.record_usage(context, "run-a", delta)
    second = await service.record_usage(context, "run-a", delta)

    assert first.total_credits == second.total_credits == 9
    assert second.usage["worker-1"].calls == 1


@pytest.mark.anyio
async def test_failed_worker_is_reported_without_cancelling_siblings() -> None:
    service, context, recorder = await _started()

    state = await service.worker_failed(
        context, "run-a", member_session_id="worker-1", error="provider timeout"
    )

    assert state.status == TeamRunStatus.RUNNING
    assert state.members["worker-1"].status == TeamMemberStatus.FAILED
    assert state.members["worker-1"].error == "provider timeout"
    assert recorder.calls == []
    assert (await service.events(context, "run-a"))[-1].type == "worker_failed"


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("reason", "budget", "tenant_budget"),
    [
        (TeamRunStopReason.RUN_BUDGET, 5, None),
        (TeamRunStopReason.TENANT_QUOTA, None, 5),
    ],
)
async def test_budget_exhaustion_stops_every_member_and_keeps_partial_results(
    reason: TeamRunStopReason,
    budget: int | None,
    tenant_budget: int | None,
) -> None:
    service, context, recorder = await _started(budget=budget, tenant_budget=tenant_budget)
    await service.worker_completed(context, "run-a", member_session_id="worker-1", result={"text": "partial"})

    state = await service.record_usage(
        context,
        "run-a",
        UsageDelta("leader", "model", credits=5, event_id="budget-event"),
    )

    assert state.status == TeamRunStatus.STOPPED
    assert state.stop_reason == reason
    assert state.total_credits == 5
    assert state.members["worker-1"].result == {"text": "partial"}
    assert state.members["leader"].status == TeamMemberStatus.CANCELLED
    assert state.members["worker-2"].status == TeamMemberStatus.CANCELLED
    assert {session for session, _, _ in recorder.calls} == {"leader", "worker-2"}
    assert all(stop_reason == reason for _, stop_reason, _ in recorder.calls)
    assert all(tenant_id == "tenant-a" for _, _, tenant_id in recorder.calls)


@pytest.mark.anyio
@pytest.mark.parametrize("reason", list(TeamRunStopReason))
async def test_user_and_authoritative_stops_are_idempotent(reason: TeamRunStopReason) -> None:
    service, context, recorder = await _started()

    first = await service.stop(context, "run-a", reason=reason)
    second = await service.stop(context, "run-a", reason=reason)

    assert first.status == second.status == TeamRunStatus.STOPPED
    assert first.finalized_at == second.finalized_at
    assert len(recorder.calls) == 3  # leader plus two workers, once each
    assert len([event for event in await service.events(context, "run-a") if event.type == "team_run_stopped"]) == 1


@pytest.mark.anyio
async def test_finalization_is_idempotent_and_rejects_late_usage() -> None:
    service, context, _ = await _started()
    await service.worker_completed(context, "run-a", member_session_id="leader")
    await service.worker_failed(context, "run-a", member_session_id="worker-1", error="failed")
    await service.worker_completed(context, "run-a", member_session_id="worker-2")

    first = await service.complete(context, "run-a")
    second = await service.complete(context, "run-a")
    assert first.status == second.status == TeamRunStatus.COMPLETED
    assert first.finalized_at == second.finalized_at

    with pytest.raises(TeamRunTerminalError):
        await service.record_usage(context, "run-a", UsageDelta("leader", "model", credits=1))


@pytest.mark.anyio
async def test_tenant_context_and_usage_validation_are_enforced() -> None:
    service, context, _ = await _started()
    with pytest.raises(InvalidUsage):
        UsageDelta("leader", "model", credits=-1)
    with pytest.raises(TeamRunNotFound):
        await service.snapshot(_context(tenant_id="tenant-b"), "run-a")
    with pytest.raises(TeamRunOwnershipError):
        await service.record_usage(context, "run-a", UsageDelta("unknown", "model", credits=1))


@pytest.mark.anyio
async def test_redis_cancellation_flags_are_tenant_process_boundary() -> None:
    class FakeRedis:
        def __init__(self) -> None:
            self.values: dict[str, str] = {}

        async def set(self, key: str, value: str, *, ex: int) -> None:
            assert ex > 0
            self.values[key] = value

        async def get(self, key: str) -> str | None:
            return self.values.get(key)

    cancellation = RedisTeamRunCancellation(FakeRedis())
    assert await cancellation.is_cancelled(session_id="worker-1", tenant_id="tenant-a") is None
    await cancellation.cancel(
        session_id="worker-1", tenant_id="tenant-a", reason=TeamRunStopReason.SECURITY
    )
    assert (
        await cancellation.is_cancelled(session_id="worker-1", tenant_id="tenant-a")
        == TeamRunStopReason.SECURITY
    )
    assert await cancellation.is_cancelled(session_id="worker-1", tenant_id="tenant-b") is None


@pytest.mark.integration
@pytest.mark.anyio
async def test_postgres_redis_store_boundary_is_explicit() -> None:
    """Run only when PostgreSQL + Redis integration fixtures are provisioned."""
    if not os.getenv("AGENTSCOPE_INTEGRATION_REDIS_URL") or not os.getenv("AGENTSCOPE_INTEGRATION_DATABASE_URL"):
        pytest.skip(
            "set AGENTSCOPE_INTEGRATION_REDIS_URL and AGENTSCOPE_INTEGRATION_DATABASE_URL "
            "for PostgreSQL/Redis Team Run integration"
        )
    pytest.skip(
        "the generated app must inject its PostgresTeamRunRepository fixture before "
        "enabling live PostgreSQL/Redis integration"
    )
{%- else %}
"""Team Run accounting tests are not configured."""
{%- endif %}
