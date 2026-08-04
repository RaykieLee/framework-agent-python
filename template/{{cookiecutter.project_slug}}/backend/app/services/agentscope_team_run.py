{%- if cookiecutter.use_agentscope and cookiecutter.enable_teams and cookiecutter.use_jwt and cookiecutter.enable_billing and cookiecutter.enable_credits_system %}
"""Durable Team Run accounting and stop propagation for AgentScope teams.

The Execution Team coordinator owns the conversation-scoped roster.  This
module owns the one billable run that wraps that roster: all model, tool,
retrieval, and memory usage is attributed to the initiating user and Active
Tenant, while per-member diagnostics remain available to the leader.

The production seam is intentionally small.  PostgreSQL is the source of
truth for the run and Redis supplies a distributed lock and cancellation
signals.  Tests use the in-process store, so no AgentScope source or private
runtime API is required here.
"""

from __future__ import annotations

import asyncio
import contextlib
from collections.abc import AsyncIterator, Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Protocol


class TeamRunError(RuntimeError):
    """Base error for rejected or unavailable Team Run operations."""


class TeamRunNotFound(TeamRunError):
    """The requested run does not exist in the Active Tenant."""


class TeamRunOwnershipError(TeamRunError):
    """A caller attempted to access a run outside its Active Tenant."""


class TeamRunTerminalError(TeamRunError):
    """A mutation was requested after a run was finalized."""


class InvalidUsage(TeamRunError):
    """A usage delta contains a negative or malformed value."""


class TeamRunStatus(StrEnum):
    """Lifecycle states persisted for one user-visible Team Run."""

    RUNNING = "running"
    STOPPING = "stopping"
    COMPLETED = "completed"
    STOPPED = "stopped"


class TeamRunStopReason(StrEnum):
    """Authoritative reasons that stop every team member."""

    USER = "user"
    RUN_BUDGET = "run_budget"
    TENANT_QUOTA = "tenant_quota"
    SECURITY = "security"


class TeamMemberStatus(StrEnum):
    """Lifecycle state of the leader or one worker inside a run."""

    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(frozen=True, slots=True)
class TeamRunContext:
    """Immutable identity binding a run to one user, tenant, and conversation."""

    tenant_id: str
    user_id: str
    conversation_id: str
    team_id: str

    def __post_init__(self) -> None:
        for name in ("tenant_id", "user_id", "conversation_id", "team_id"):
            if not str(getattr(self, name)).strip():
                raise TeamRunOwnershipError(f"{name} is required for a Team Run")


@dataclass(frozen=True, slots=True)
class UsageDelta:
    """One model/tool/retrieval/memory usage observation from a participant."""

    member_session_id: str
    kind: str
    credits: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cached_tokens: int = 0
    event_id: str | None = None

    def __post_init__(self) -> None:
        if not self.member_session_id.strip():
            raise InvalidUsage("member_session_id is required")
        if self.kind not in {"model", "tool", "retrieval", "memory"}:
            raise InvalidUsage("usage kind must be model, tool, retrieval, or memory")
        for name in ("credits", "input_tokens", "output_tokens", "cached_tokens"):
            if int(getattr(self, name)) < 0:
                raise InvalidUsage(f"{name} must not be negative")

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens + self.cached_tokens

    def to_payload(self) -> dict[str, Any]:
        return {
            "member_session_id": self.member_session_id,
            "kind": self.kind,
            "credits": self.credits,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cached_tokens": self.cached_tokens,
            "event_id": self.event_id,
        }


@dataclass(slots=True)
class MemberUsage:
    """Per-member diagnostics that are never billed as separate runs."""

    credits: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cached_tokens: int = 0
    calls: int = 0
    by_kind: dict[str, int] = field(default_factory=dict)

    def add(self, delta: UsageDelta) -> None:
        self.credits += delta.credits
        self.input_tokens += delta.input_tokens
        self.output_tokens += delta.output_tokens
        self.cached_tokens += delta.cached_tokens
        self.calls += 1
        self.by_kind[delta.kind] = self.by_kind.get(delta.kind, 0) + delta.credits

    def to_payload(self) -> dict[str, Any]:
        return {
            "credits": self.credits,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cached_tokens": self.cached_tokens,
            "calls": self.calls,
            "by_kind": dict(self.by_kind),
        }

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "MemberUsage":
        return cls(
            credits=int(payload.get("credits", 0)),
            input_tokens=int(payload.get("input_tokens", 0)),
            output_tokens=int(payload.get("output_tokens", 0)),
            cached_tokens=int(payload.get("cached_tokens", 0)),
            calls=int(payload.get("calls", 0)),
            by_kind={str(k): int(v) for k, v in dict(payload.get("by_kind", {})).items()},
        )


@dataclass(slots=True)
class TeamRunMember:
    session_id: str
    role: str
    status: TeamMemberStatus = TeamMemberStatus.RUNNING
    error: str | None = None
    result: Any = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "role": self.role,
            "status": self.status.value,
            "error": self.error,
            "result": self.result,
        }

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "TeamRunMember":
        return cls(
            session_id=str(payload["session_id"]),
            role=str(payload["role"]),
            status=TeamMemberStatus(str(payload.get("status", TeamMemberStatus.RUNNING.value))),
            error=payload.get("error"),
            result=payload.get("result"),
        )


@dataclass(slots=True)
class TeamRunState:
    """Serializable account and state machine for one Team Run."""

    run_id: str
    context: TeamRunContext
    leader_session_id: str
    members: dict[str, TeamRunMember]
    run_budget_credits: int | None = None
    tenant_budget_credits: int | None = None
    status: TeamRunStatus = TeamRunStatus.RUNNING
    stop_reason: TeamRunStopReason | None = None
    usage: dict[str, MemberUsage] = field(default_factory=dict)
    accepted_usage_events: set[str] = field(default_factory=set)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    finalized_at: datetime | None = None
    version: int = 0

    @property
    def total_credits(self) -> int:
        return sum(item.credits for item in self.usage.values())

    @property
    def total_input_tokens(self) -> int:
        return sum(item.input_tokens for item in self.usage.values())

    @property
    def total_output_tokens(self) -> int:
        return sum(item.output_tokens for item in self.usage.values())

    @property
    def total_cached_tokens(self) -> int:
        return sum(item.cached_tokens for item in self.usage.values())

    @property
    def terminal(self) -> bool:
        return self.status in {TeamRunStatus.COMPLETED, TeamRunStatus.STOPPED}

    def to_payload(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "tenant_id": self.context.tenant_id,
            "user_id": self.context.user_id,
            "conversation_id": self.context.conversation_id,
            "team_id": self.context.team_id,
            "leader_session_id": self.leader_session_id,
            "members": [member.to_payload() for member in self.members.values()],
            "run_budget_credits": self.run_budget_credits,
            "tenant_budget_credits": self.tenant_budget_credits,
            "status": self.status.value,
            "stop_reason": self.stop_reason.value if self.stop_reason else None,
            "usage": {session_id: item.to_payload() for session_id, item in self.usage.items()},
            "accepted_usage_events": sorted(self.accepted_usage_events),
            "created_at": self.created_at.isoformat(),
            "finalized_at": self.finalized_at.isoformat() if self.finalized_at else None,
            "version": self.version,
        }

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "TeamRunState":
        def _timestamp(value: Any) -> datetime | None:
            return datetime.fromisoformat(str(value)) if value else None

        context = TeamRunContext(
            tenant_id=str(payload["tenant_id"]),
            user_id=str(payload["user_id"]),
            conversation_id=str(payload["conversation_id"]),
            team_id=str(payload["team_id"]),
        )
        members = {
            str(member["session_id"]): TeamRunMember.from_payload(member)
            for member in payload.get("members", [])
        }
        return cls(
            run_id=str(payload["run_id"]),
            context=context,
            leader_session_id=str(payload["leader_session_id"]),
            members=members,
            run_budget_credits=payload.get("run_budget_credits"),
            tenant_budget_credits=payload.get("tenant_budget_credits"),
            status=TeamRunStatus(str(payload.get("status", TeamRunStatus.RUNNING.value))),
            stop_reason=(
                TeamRunStopReason(str(payload["stop_reason"]))
                if payload.get("stop_reason")
                else None
            ),
            usage={
                str(session_id): MemberUsage.from_payload(item)
                for session_id, item in dict(payload.get("usage", {})).items()
            },
            accepted_usage_events={str(item) for item in payload.get("accepted_usage_events", [])},
            created_at=_timestamp(payload.get("created_at")) or datetime.now(UTC),
            finalized_at=_timestamp(payload.get("finalized_at")),
            version=int(payload.get("version", 0)),
        )


@dataclass(frozen=True, slots=True)
class TeamRunEvent:
    type: str
    run_id: str
    tenant_id: str
    user_id: str
    conversation_id: str
    data: Mapping[str, Any]
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_payload(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "run_id": self.run_id,
            "tenant_id": self.tenant_id,
            "user_id": self.user_id,
            "conversation_id": self.conversation_id,
            "data": dict(self.data),
            "occurred_at": self.occurred_at.isoformat(),
        }


class TeamRunStore(Protocol):
    """Persistence seam: PostgreSQL state + Redis coordination in production."""

    def lock(self, key: str) -> contextlib.AbstractAsyncContextManager[None]: ...

    async def get(self, key: str) -> TeamRunState | None: ...

    async def put(self, key: str, state: TeamRunState) -> None: ...

    async def append_event(self, key: str, event: TeamRunEvent) -> None: ...

    async def list_events(self, key: str) -> list[TeamRunEvent]: ...


class InMemoryTeamRunStore:
    """Behaviorally complete in-process store used by unit tests."""

    def __init__(self) -> None:
        self.states: dict[str, TeamRunState] = {}
        self.events: dict[str, list[TeamRunEvent]] = {}
        self._locks: dict[str, asyncio.Lock] = {}

    def lock(self, key: str) -> contextlib.AbstractAsyncContextManager[None]:
        @contextlib.asynccontextmanager
        async def _lock() -> AsyncIterator[None]:
            async with self._locks.setdefault(key, asyncio.Lock()):
                yield

        return _lock()

    async def get(self, key: str) -> TeamRunState | None:
        state = self.states.get(key)
        if state is None:
            return None
        return TeamRunState.from_payload(state.to_payload())

    async def put(self, key: str, state: TeamRunState) -> None:
        self.states[key] = TeamRunState.from_payload(state.to_payload())

    async def append_event(self, key: str, event: TeamRunEvent) -> None:
        self.events.setdefault(key, []).append(event)

    async def list_events(self, key: str) -> list[TeamRunEvent]:
        return list(self.events.get(key, []))


class PostgresTeamRunRepository(Protocol):
    """Control-Plane repository implemented by generated PostgreSQL projects."""

    async def get_team_run(self, *, key: str) -> TeamRunState | None: ...

    async def save_team_run(self, *, key: str, state: TeamRunState) -> None: ...

    async def append_team_run_event(self, *, key: str, event: TeamRunEvent) -> None: ...

    async def list_team_run_events(self, *, key: str) -> list[TeamRunEvent]: ...


class RedisPostgresTeamRunStore:
    """Production adapter using PostgreSQL as truth and Redis for locks."""

    def __init__(self, repository: PostgresTeamRunRepository, redis: Any) -> None:
        self.repository = repository
        self.redis = redis

    def lock(self, key: str) -> contextlib.AbstractAsyncContextManager[None]:
        @contextlib.asynccontextmanager
        async def _lock() -> AsyncIterator[None]:
            lock = self.redis.lock(f"{key}:lock", timeout=120, blocking_timeout=30)
            acquired = await lock.acquire()
            if not acquired:
                raise TeamRunError("another process owns this Team Run")
            try:
                yield
            finally:
                with contextlib.suppress(Exception):
                    await lock.release()

        return _lock()

    async def get(self, key: str) -> TeamRunState | None:
        return await self.repository.get_team_run(key=key)

    async def put(self, key: str, state: TeamRunState) -> None:
        await self.repository.save_team_run(key=key, state=state)

    async def append_event(self, key: str, event: TeamRunEvent) -> None:
        await self.repository.append_team_run_event(key=key, event=event)

    async def list_events(self, key: str) -> list[TeamRunEvent]:
        return await self.repository.list_team_run_events(key=key)


class WorkerCancellation(Protocol):
    async def cancel(self, *, session_id: str, reason: TeamRunStopReason) -> None: ...


class TenantBudgetResolver(Protocol):
    async def current_budget(self, *, tenant_id: str) -> int | None: ...


class AgentScopeTeamRunService:
    """Aggregate usage and coordinate cancellation for one Execution Team."""

    def __init__(
        self,
        store: TeamRunStore,
        *,
        cancellation: WorkerCancellation | None = None,
        tenant_budget_resolver: TenantBudgetResolver | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.store = store
        self.cancellation = cancellation
        self.tenant_budget_resolver = tenant_budget_resolver
        self.clock = clock or (lambda: datetime.now(UTC))

    async def start(
        self,
        context: TeamRunContext,
        *,
        run_id: str,
        leader_session_id: str,
        worker_session_ids: Sequence[str],
        run_budget_credits: int | None = None,
        tenant_budget_credits: int | None = None,
    ) -> TeamRunState:
        """Create a single billable run for a leader and flat worker roster."""
        self._validate_budget(run_budget_credits, "run_budget_credits")
        self._validate_budget(tenant_budget_credits, "tenant_budget_credits")
        if not run_id.strip() or not leader_session_id.strip():
            raise TeamRunOwnershipError("run_id and leader_session_id are required")
        sessions = [leader_session_id, *worker_session_ids]
        if len(set(sessions)) != len(sessions) or any(not item.strip() for item in sessions):
            raise TeamRunOwnershipError("Team Run members must be unique and non-empty")
        key = self._key(context, run_id)
        async with self.store.lock(key):
            existing = await self.store.get(key)
            if existing is not None:
                return self._assert_context(existing, context)
            if tenant_budget_credits is None and self.tenant_budget_resolver is not None:
                tenant_budget_credits = await self.tenant_budget_resolver.current_budget(
                    tenant_id=context.tenant_id
                )
                self._validate_budget(tenant_budget_credits, "tenant_budget_credits")
            state = TeamRunState(
                run_id=run_id,
                context=context,
                leader_session_id=leader_session_id,
                members={
                    session_id: TeamRunMember(
                        session_id=session_id,
                        role="leader" if session_id == leader_session_id else "worker",
                    )
                    for session_id in sessions
                },
                run_budget_credits=run_budget_credits,
                tenant_budget_credits=tenant_budget_credits,
            )
            await self.store.put(key, state)
            await self._emit(state, "team_run_started", {"member_count": len(sessions)})
            return state

    async def record_usage(
        self,
        context: TeamRunContext,
        run_id: str,
        usage: UsageDelta,
    ) -> TeamRunState:
        """Accept one idempotent usage event and stop at either budget boundary."""
        key = self._key(context, run_id)
        async with self.store.lock(key):
            state = await self._load(key, context)
            if usage.member_session_id not in state.members:
                raise TeamRunOwnershipError("usage member is not part of this Team Run")
            if usage.event_id and usage.event_id in state.accepted_usage_events:
                return state
            if state.terminal:
                raise TeamRunTerminalError("Team Run is already finalized")
            state.usage.setdefault(usage.member_session_id, MemberUsage()).add(usage)
            if usage.event_id:
                state.accepted_usage_events.add(usage.event_id)
            state.version += 1
            await self.store.put(key, state)
            await self._emit(
                state,
                "usage_recorded",
                {"usage": usage.to_payload(), "total_credits": state.total_credits},
            )
            if self._budget_exhausted(state):
                reason = (
                    TeamRunStopReason.RUN_BUDGET
                    if state.run_budget_credits is not None
                    and state.total_credits >= state.run_budget_credits
                    else TeamRunStopReason.TENANT_QUOTA
                )
                return await self._stop_locked(state, reason)
            return state

    async def worker_completed(
        self,
        context: TeamRunContext,
        run_id: str,
        *,
        member_session_id: str,
        result: Any = None,
    ) -> TeamRunState:
        """Record partial completion without finalizing until all members finish."""
        return await self._set_member_terminal(
            context,
            run_id,
            member_session_id=member_session_id,
            status=TeamMemberStatus.COMPLETED,
            result=result,
        )

    async def worker_failed(
        self,
        context: TeamRunContext,
        run_id: str,
        *,
        member_session_id: str,
        error: str,
    ) -> TeamRunState:
        """Report one failure to the leader while siblings continue running."""
        if not error.strip():
            raise TeamRunError("worker failure must include an error")
        return await self._set_member_terminal(
            context,
            run_id,
            member_session_id=member_session_id,
            status=TeamMemberStatus.FAILED,
            error=error,
        )

    async def stop(
        self,
        context: TeamRunContext,
        run_id: str,
        *,
        reason: TeamRunStopReason,
    ) -> TeamRunState:
        """Stop leader and every active worker; repeated calls are harmless."""
        key = self._key(context, run_id)
        async with self.store.lock(key):
            state = await self._load(key, context)
            if state.terminal:
                return state
            return await self._stop_locked(state, reason)

    async def complete(self, context: TeamRunContext, run_id: str) -> TeamRunState:
        """Finalize successful work exactly once after all members report."""
        key = self._key(context, run_id)
        async with self.store.lock(key):
            state = await self._load(key, context)
            if state.terminal:
                return state
            if any(member.status == TeamMemberStatus.RUNNING for member in state.members.values()):
                raise TeamRunError("cannot complete while a Team Run member is still running")
            state.status = TeamRunStatus.COMPLETED
            state.finalized_at = self.clock()
            state.version += 1
            await self.store.put(key, state)
            await self._emit(state, "team_run_completed", {"total_credits": state.total_credits})
            return state

    async def snapshot(self, context: TeamRunContext, run_id: str) -> TeamRunState:
        return await self._load(self._key(context, run_id), context)

    async def events(self, context: TeamRunContext, run_id: str) -> list[TeamRunEvent]:
        state = await self.snapshot(context, run_id)
        return await self.store.list_events(self._key(state.context, state.run_id))

    async def _set_member_terminal(
        self,
        context: TeamRunContext,
        run_id: str,
        *,
        member_session_id: str,
        status: TeamMemberStatus,
        result: Any = None,
        error: str | None = None,
    ) -> TeamRunState:
        key = self._key(context, run_id)
        async with self.store.lock(key):
            state = await self._load(key, context)
            member = state.members.get(member_session_id)
            if member is None:
                raise TeamRunOwnershipError("member is not part of this Team Run")
            if state.terminal:
                return state
            if member.status in {
                TeamMemberStatus.COMPLETED,
                TeamMemberStatus.FAILED,
                TeamMemberStatus.CANCELLED,
            }:
                return state
            member.status = status
            member.result = result
            member.error = error
            state.version += 1
            await self.store.put(key, state)
            await self._emit(
                state,
                "worker_failed" if status == TeamMemberStatus.FAILED else "member_completed",
                {"member_session_id": member_session_id, "error": error, "result": result},
            )
            return state

    async def _stop_locked(self, state: TeamRunState, reason: TeamRunStopReason) -> TeamRunState:
        if state.terminal:
            return state
        state.status = TeamRunStatus.STOPPING
        state.stop_reason = reason
        await self.store.put(self._key(state.context, state.run_id), state)
        await self._emit(state, "team_run_stopping", {"reason": reason.value})
        for member in state.members.values():
            if member.status == TeamMemberStatus.RUNNING:
                try:
                    await self._cancel(member.session_id, reason)
                except Exception as exc:
                    # A crashed cancellation transport must not leave the
                    # authoritative run in ``stopping`` forever.  The member
                    # is still marked cancelled and the failure is visible to
                    # the leader through the event stream.
                    await self._emit(
                        state,
                        "member_cancellation_failed",
                        {"member_session_id": member.session_id, "error": str(exc)},
                    )
                member.status = TeamMemberStatus.CANCELLED
        state.status = TeamRunStatus.STOPPED
        state.finalized_at = self.clock()
        state.version += 1
        await self.store.put(self._key(state.context, state.run_id), state)
        await self._emit(
            state,
            "team_run_stopped",
            {"reason": reason.value, "total_credits": state.total_credits},
        )
        return state

    async def _cancel(self, session_id: str, reason: TeamRunStopReason) -> None:
        if self.cancellation is None:
            return
        await self.cancellation.cancel(session_id=session_id, reason=reason)

    async def _emit(self, state: TeamRunState, event_type: str, data: Mapping[str, Any]) -> None:
        await self.store.append_event(
            self._key(state.context, state.run_id),
            TeamRunEvent(
                type=event_type,
                run_id=state.run_id,
                tenant_id=state.context.tenant_id,
                user_id=state.context.user_id,
                conversation_id=state.context.conversation_id,
                data=dict(data),
            ),
        )

    async def _load(self, key: str, context: TeamRunContext) -> TeamRunState:
        state = await self.store.get(key)
        if state is None:
            raise TeamRunNotFound("Team Run not found")
        return self._assert_context(state, context)

    @staticmethod
    def _assert_context(state: TeamRunState, context: TeamRunContext) -> TeamRunState:
        if state.context != context:
            raise TeamRunOwnershipError("Team Run is outside the Active Tenant")
        return state

    @staticmethod
    def _validate_budget(value: int | None, name: str) -> None:
        if value is not None and value < 0:
            raise InvalidUsage(f"{name} must not be negative")

    @staticmethod
    def _budget_exhausted(state: TeamRunState) -> bool:
        return (
            state.run_budget_credits is not None and state.total_credits >= state.run_budget_credits
        ) or (
            state.tenant_budget_credits is not None
            and state.total_credits >= state.tenant_budget_credits
        )

    @staticmethod
    def _key(context: TeamRunContext, run_id: str) -> str:
        return (
            f"agentscope:team-run:{_safe(context.tenant_id)}:"
            f"{_safe(context.user_id)}:{_safe(context.conversation_id)}:{_safe(run_id)}"
        )


def _safe(value: str) -> str:
    return "".join(char if char.isalnum() or char in "._:-" else "_" for char in value)[:160] or "empty"


__all__ = [
    "AgentScopeTeamRunService",
    "InMemoryTeamRunStore",
    "InvalidUsage",
    "MemberUsage",
    "PostgresTeamRunRepository",
    "RedisPostgresTeamRunStore",
    "TeamMemberStatus",
    "TeamRunContext",
    "TeamRunError",
    "TeamRunEvent",
    "TeamRunNotFound",
    "TeamRunState",
    "TeamRunStatus",
    "TeamRunStopReason",
    "TeamRunStore",
    "TeamRunTerminalError",
    "TeamRunOwnershipError",
    "TeamRunMember",
    "UsageDelta",
]
{%- else %}
"""Team Run accounting is not configured."""
{%- endif %}
