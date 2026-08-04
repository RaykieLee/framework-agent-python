{%- if cookiecutter.use_agentscope and cookiecutter.enable_teams and cookiecutter.use_jwt %}
"""Conversation-scoped AgentScope Execution Team coordination.

The generated application's Control Plane owns tenant and Agent Definition
authorization.  This adapter owns only the short-lived execution roster and
maps product messages onto AgentScope's public ``MessageBus`` primitives.  It
does not import AgentScope's private team tools or expose native objects over
the product API.
"""

from __future__ import annotations

import json
import re
from collections.abc import AsyncGenerator, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import uuid4

from agentscope.app.message_bus import MessageBus
from agentscope.app.storage import TeamData, TeamMember, TeamRecord

from app.core.exceptions import AuthorizationError, NotFoundError, ValidationError
from app.schemas.agentscope_agent_definition import AgentDefinitionRuntime


MAX_WORKERS = 6
TEAM_STATE_TTL_SECONDS = 86_400
TEAM_EVENT_MAX_LEN = 1_000


class ExecutionTeamError(RuntimeError):
    """Base error for a rejected or unavailable team operation."""


class ActiveTenantRequired(ExecutionTeamError):
    """The execution did not carry one authorized Active Tenant."""


class NestedTeamNotAllowed(ExecutionTeamError):
    """Workers cannot create teams or additional workers."""


class WorkerLimitExceeded(ExecutionTeamError):
    """A team would exceed the product's six-worker limit."""


class AgentDefinitionUnavailable(ExecutionTeamError):
    """A requested Agent Definition is not enabled for the Active Tenant."""


class NotTeamLeader(ExecutionTeamError):
    """The operation requires the initiating leader session."""


class ExecutionTeamExists(ExecutionTeamError):
    """A conversation already has an active Execution Team."""


class EnabledAgentDefinitionResolver(Protocol):
    """Control-Plane seam for the definitions enabled in one tenant."""

    async def list_enabled(
        self,
        *,
        tenant_id: str,
        user_id: str,
    ) -> Sequence[AgentDefinitionRuntime]: ...


@dataclass(frozen=True, slots=True)
class ExecutionTeamContext:
    """Immutable identity bound to every team operation."""

    tenant_id: str
    user_id: str
    conversation_id: str
    active_tenant_role: str = "member"

    def __post_init__(self) -> None:
        for name in ("tenant_id", "user_id", "conversation_id"):
            if not str(getattr(self, name)).strip():
                raise ActiveTenantRequired(f"{name} is required for an Execution Team")
        if self.active_tenant_role == "viewer":
            raise AuthorizationError(message="Organization Viewers cannot start an Execution Team")


@dataclass(slots=True)
class ExecutionWorker:
    """Product roster projection for one Agent Definition worker."""

    definition_slug: str
    definition_version: int
    role: str
    session_id: str
    status: str = "pending"
    error: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "definition_slug": self.definition_slug,
            "definition_version": self.definition_version,
            "role": self.role,
            "session_id": self.session_id,
            "status": self.status,
            "error": self.error,
        }

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "ExecutionWorker":
        return cls(
            definition_slug=str(payload["definition_slug"]),
            definition_version=int(payload["definition_version"]),
            role=str(payload["role"]),
            session_id=str(payload["session_id"]),
            status=str(payload.get("status", "pending")),
            error=payload.get("error"),
        )


@dataclass(slots=True)
class ExecutionTeamState:
    """Durable, tenant-prefixed state for one conversation's team."""

    team_id: str
    context: ExecutionTeamContext
    leader_session_id: str
    name: str
    description: str
    workers: dict[str, ExecutionWorker] = field(default_factory=dict)
    status: str = "active"

    @property
    def native_record(self) -> TeamRecord:
        """Return AgentScope's public native roster model for adapters."""
        return TeamRecord(
            user_id=self.context.user_id,
            session_id=self.leader_session_id,
            data=TeamData(
                name=self.name,
                description=self.description,
                members=[
                    TeamMember(
                        owner_id=self.context.user_id,
                        agent_id=worker.definition_slug,
                        session_id=worker.session_id,
                        role="created",
                    )
                    for worker in self.workers.values()
                ],
            ),
        )

    def to_payload(self) -> dict[str, Any]:
        return {
            "team_id": self.team_id,
            "tenant_id": self.context.tenant_id,
            "user_id": self.context.user_id,
            "conversation_id": self.context.conversation_id,
            "active_tenant_role": self.context.active_tenant_role,
            "leader_session_id": self.leader_session_id,
            "name": self.name,
            "description": self.description,
            "status": self.status,
            "workers": [worker.to_payload() for worker in self.workers.values()],
        }

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "ExecutionTeamState":
        context = ExecutionTeamContext(
            tenant_id=str(payload["tenant_id"]),
            user_id=str(payload["user_id"]),
            conversation_id=str(payload["conversation_id"]),
            active_tenant_role=str(payload.get("active_tenant_role", "member")),
        )
        workers = {
            worker["definition_slug"]: ExecutionWorker.from_payload(worker)
            for worker in payload.get("workers", [])
        }
        return cls(
            team_id=str(payload["team_id"]),
            context=context,
            leader_session_id=str(payload["leader_session_id"]),
            name=str(payload["name"]),
            description=str(payload.get("description", "")),
            workers=workers,
            status=str(payload.get("status", "active")),
        )


@dataclass(frozen=True, slots=True)
class TeamReconnect:
    """State plus replayed events returned when a client reconnects."""

    state: ExecutionTeamState
    events: tuple[dict[str, Any], ...]


class AgentScopeExecutionTeamCoordinator:
    """Coordinate one conversation team through AgentScope's public bus."""

    def __init__(
        self,
        message_bus: MessageBus,
        definition_resolver: EnabledAgentDefinitionResolver,
    ) -> None:
        self.message_bus = message_bus
        self.definition_resolver = definition_resolver

    async def create_team(
        self,
        context: ExecutionTeamContext,
        *,
        leader_session_id: str,
        requested_definition_slugs: Sequence[str] | None = None,
        description: str = "",
        parent_team_id: str | None = None,
        requesting_session_id: str | None = None,
    ) -> ExecutionTeamState:
        """Create one flat roster from definitions enabled for ``context``."""
        self._validate_context(context)
        if parent_team_id:
            raise NestedTeamNotAllowed("Execution Teams are single-level; workers cannot create teams")
        if not leader_session_id.strip():
            raise ValidationError(message="leader_session_id is required")
        if requesting_session_id is not None and requesting_session_id != leader_session_id:
            raise NotTeamLeader("Only the initiating leader may create workers")

        index_namespace = self._conversation_namespace(context)
        existing = await self.message_bus.registry_getall(index_namespace)
        if existing.get("team_id"):
            existing_state = await self._load(context, existing["team_id"])
            if existing_state.status == "active":
                if any(
                    worker.session_id == requesting_session_id
                    for worker in existing_state.workers.values()
                ):
                    raise NestedTeamNotAllowed("Workers cannot create nested teams")
                raise ExecutionTeamExists("The conversation already has an active Execution Team")

        definitions = await self.definition_resolver.list_enabled(
            tenant_id=context.tenant_id,
            user_id=context.user_id,
        )
        by_slug = {definition.slug: definition for definition in definitions}
        slugs = list(requested_definition_slugs or by_slug.keys())
        if len(slugs) > MAX_WORKERS:
            raise WorkerLimitExceeded(f"An Execution Team may contain at most {MAX_WORKERS} workers")
        if len(set(slugs)) != len(slugs):
            raise ValidationError(message="Agent Definition slugs must be unique within a team")
        unavailable = [slug for slug in slugs if slug not in by_slug]
        if unavailable:
            raise AgentDefinitionUnavailable(
                f"Agent Definitions are not enabled for the Active Tenant: {', '.join(unavailable)}"
            )

        team_id = f"team-{uuid4().hex}"
        state = ExecutionTeamState(
            team_id=team_id,
            context=context,
            leader_session_id=leader_session_id,
            name=f"conversation-{context.conversation_id}",
            description=description,
        )
        for slug in slugs:
            definition = by_slug[slug]
            state.workers[slug] = ExecutionWorker(
                definition_slug=definition.slug,
                definition_version=definition.version,
                role=definition.role,
                session_id=f"{team_id}:worker:{_safe_component(slug)}",
            )
        await self._persist(state)
        await self._emit(state, "team_created", {"team": state.to_payload()})
        return state

    async def add_worker(
        self,
        context: ExecutionTeamContext,
        team_id: str,
        *,
        actor_session_id: str,
        definition_slug: str,
    ) -> ExecutionTeamState:
        """Dynamically add one enabled worker; only the leader may do so."""
        state = await self._load_for_context(context, team_id)
        if actor_session_id != state.leader_session_id:
            raise NotTeamLeader("Only the initiating leader may create workers")
        if len(state.workers) >= MAX_WORKERS:
            raise WorkerLimitExceeded(f"An Execution Team may contain at most {MAX_WORKERS} workers")
        if definition_slug in state.workers:
            raise ValidationError(message="Agent Definition is already on the team")
        definitions = await self.definition_resolver.list_enabled(
            tenant_id=context.tenant_id,
            user_id=context.user_id,
        )
        definition = next((item for item in definitions if item.slug == definition_slug), None)
        if definition is None:
            raise AgentDefinitionUnavailable(
                f"Agent Definition is not enabled for the Active Tenant: {definition_slug}"
            )
        state.workers[definition_slug] = ExecutionWorker(
            definition_slug=definition.slug,
            definition_version=definition.version,
            role=definition.role,
            session_id=f"{team_id}:worker:{_safe_component(definition.slug)}",
        )
        await self._persist(state)
        await self._emit(state, "worker_created", {"worker": state.workers[definition_slug].to_payload()})
        return state

    async def direct_message(
        self,
        context: ExecutionTeamContext,
        team_id: str,
        *,
        sender_session_id: str,
        recipient: str,
        content: str,
    ) -> str:
        """Deliver a direct message to a worker or the team leader."""
        state = await self._load_for_context(context, team_id)
        self._assert_member(state, sender_session_id)
        if not content.strip():
            raise ValidationError(message="Team message content is required")
        recipient_session = self._recipient_session(state, recipient)
        entry_id = await self.message_bus.queue_push(
            self._inbox_key(state, recipient_session),
            self._message_payload(state, sender_session_id, content, broadcast=False),
            ttl_secs=TEAM_STATE_TTL_SECONDS,
        )
        await self._emit(
            state,
            "direct_message",
            {"sender_session_id": sender_session_id, "recipient": recipient, "content": content},
        )
        return entry_id

    async def broadcast(
        self,
        context: ExecutionTeamContext,
        team_id: str,
        *,
        sender_session_id: str,
        content: str,
    ) -> int:
        """Fan a message out to every other member's durable inbox."""
        state = await self._load_for_context(context, team_id)
        self._assert_member(state, sender_session_id)
        if not content.strip():
            raise ValidationError(message="Team message content is required")
        recipients = [state.leader_session_id, *(worker.session_id for worker in state.workers.values())]
        recipients = [session_id for session_id in recipients if session_id != sender_session_id]
        payload = self._message_payload(state, sender_session_id, content, broadcast=True)
        for recipient_session in recipients:
            await self.message_bus.queue_push(
                self._inbox_key(state, recipient_session),
                payload,
                ttl_secs=TEAM_STATE_TTL_SECONDS,
            )
        await self._emit(
            state,
            "broadcast_message",
            {"sender_session_id": sender_session_id, "content": content, "recipient_count": len(recipients)},
        )
        return len(recipients)

    async def drain_inbox(
        self,
        context: ExecutionTeamContext,
        team_id: str,
        *,
        recipient_session_id: str,
        max_count: int = 100,
    ) -> list[dict[str, Any]]:
        """Consume a member's durable inbox using the public bus queue API."""
        state = await self._load_for_context(context, team_id)
        self._assert_member(state, recipient_session_id)
        entries = await self.message_bus.queue_drain(
            self._inbox_key(state, recipient_session_id),
            max_count=max_count,
        )
        return [payload for _entry_id, payload in entries]

    async def worker_completed(
        self,
        context: ExecutionTeamContext,
        team_id: str,
        *,
        worker_session_id: str,
        result: Any = None,
    ) -> ExecutionTeamState:
        """Record an isolated worker completion and publish its roster event."""
        state = await self._load_for_context(context, team_id)
        worker = self._worker_by_session(state, worker_session_id)
        worker.status = "completed"
        worker.error = None
        self._refresh_terminal_status(state)
        await self._persist(state)
        await self._emit(state, "worker_completed", {"worker_session_id": worker_session_id, "result": result})
        return state

    async def worker_failed(
        self,
        context: ExecutionTeamContext,
        team_id: str,
        *,
        worker_session_id: str,
        error: str,
    ) -> ExecutionTeamState:
        """Record an isolated worker failure without cancelling siblings."""
        state = await self._load_for_context(context, team_id)
        worker = self._worker_by_session(state, worker_session_id)
        worker.status = "failed"
        worker.error = error
        self._refresh_terminal_status(state)
        await self._persist(state)
        await self._emit(state, "worker_failed", {"worker_session_id": worker_session_id, "error": error})
        return state

    async def reconnect(
        self,
        context: ExecutionTeamContext,
        team_id: str,
        *,
        since: str | None = None,
    ) -> TeamReconnect:
        """Reload tenant-bound state and replay events after a disconnect."""
        state = await self._load_for_context(context, team_id)
        entries = await self.message_bus.log_read(self._events_key(state), since=since)
        events = tuple(payload for _entry_id, payload in entries)
        await self._emit(state, "reconnected", {"since": since, "replayed_count": len(events)})
        return TeamReconnect(state=state, events=events)

    async def subscribe(
        self,
        context: ExecutionTeamContext,
        team_id: str,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Subscribe to live team events; callers may reconnect via replay."""
        state = await self._load_for_context(context, team_id)
        async for event in self.message_bus.subscribe(self._events_key(state)):
            yield event

    async def _load_for_context(
        self,
        context: ExecutionTeamContext,
        team_id: str,
    ) -> ExecutionTeamState:
        self._validate_context(context)
        try:
            state = await self._load(context, team_id)
        except NotFoundError as exc:
            # Do not reveal whether a team id exists under another tenant.
            raise AuthorizationError(message="Execution Team is outside the Active Tenant") from exc
        if state.context != context:
            raise ActiveTenantRequired("Execution Team belongs to a different Active Tenant or user")
        return state

    async def _load(self, context: ExecutionTeamContext, team_id: str) -> ExecutionTeamState:
        records = await self.message_bus.registry_getall(self._state_namespace(context, team_id))
        raw = records.get("state")
        if raw is None:
            raise NotFoundError(message="Execution Team not found")
        try:
            return ExecutionTeamState.from_payload(json.loads(raw))
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise NotFoundError(message="Execution Team state is invalid") from exc

    async def _persist(self, state: ExecutionTeamState) -> None:
        await self.message_bus.registry_set(
            self._state_namespace(state.context, state.team_id),
            "state",
            json.dumps(state.to_payload(), separators=(",", ":")),
            ttl_secs=TEAM_STATE_TTL_SECONDS,
        )
        await self.message_bus.registry_set(
            self._conversation_namespace(state.context),
            "team_id",
            state.team_id,
            ttl_secs=TEAM_STATE_TTL_SECONDS,
        )

    async def _emit(self, state: ExecutionTeamState, event_type: str, data: dict[str, Any]) -> str:
        event = {
            "type": event_type,
            "team_id": state.team_id,
            "tenant_id": state.context.tenant_id,
            "user_id": state.context.user_id,
            "conversation_id": state.context.conversation_id,
            "occurred_at": datetime.now(UTC).isoformat(),
            "data": data,
        }
        entry_id = await self.message_bus.log_append(
            self._events_key(state),
            event,
            ttl_secs=TEAM_STATE_TTL_SECONDS,
            max_len=TEAM_EVENT_MAX_LEN,
        )
        await self.message_bus.publish(self._events_key(state), {**event, "_entry_id": entry_id})
        return entry_id

    @staticmethod
    def _validate_context(context: ExecutionTeamContext) -> None:
        if not isinstance(context, ExecutionTeamContext):
            raise ActiveTenantRequired("Execution Team operations require an Active Tenant context")

    @staticmethod
    def _assert_member(state: ExecutionTeamState, session_id: str) -> None:
        if session_id != state.leader_session_id and all(
            worker.session_id != session_id for worker in state.workers.values()
        ):
            raise AuthorizationError(message="Session is not a member of this Execution Team")

    @staticmethod
    def _worker_by_session(state: ExecutionTeamState, session_id: str) -> ExecutionWorker:
        for worker in state.workers.values():
            if worker.session_id == session_id:
                return worker
        raise NotFoundError(message="Execution Team worker not found")

    @staticmethod
    def _recipient_session(state: ExecutionTeamState, recipient: str) -> str:
        if recipient == "leader" or recipient == state.leader_session_id:
            return state.leader_session_id
        worker = state.workers.get(recipient)
        if worker is not None:
            return worker.session_id
        try:
            return AgentScopeExecutionTeamCoordinator._worker_by_session(state, recipient).session_id
        except NotFoundError as exc:
            raise NotFoundError(message="Execution Team recipient not found") from exc

    @staticmethod
    def _message_payload(
        state: ExecutionTeamState,
        sender_session_id: str,
        content: str,
        *,
        broadcast: bool,
    ) -> dict[str, Any]:
        return {
            "type": "team_message",
            "team_id": state.team_id,
            "tenant_id": state.context.tenant_id,
            "conversation_id": state.context.conversation_id,
            "sender_session_id": sender_session_id,
            "broadcast": broadcast,
            "content": content,
        }

    @staticmethod
    def _refresh_terminal_status(state: ExecutionTeamState) -> None:
        statuses = {worker.status for worker in state.workers.values()}
        if statuses and statuses <= {"completed", "failed"}:
            state.status = "failed" if "failed" in statuses else "completed"

    @staticmethod
    def _conversation_namespace(context: ExecutionTeamContext) -> str:
        return f"agentscope:execution-team:{_safe_component(context.tenant_id)}:{_safe_component(context.user_id)}:{_safe_component(context.conversation_id)}"

    @staticmethod
    def _state_namespace(context: ExecutionTeamContext, team_id: str) -> str:
        return f"agentscope:execution-team-state:{_safe_component(context.tenant_id)}:{_safe_component(team_id)}"

    @staticmethod
    def _events_key(state: ExecutionTeamState) -> str:
        return f"agentscope:execution-team-events:{_safe_component(state.context.tenant_id)}:{_safe_component(state.team_id)}"

    @staticmethod
    def _inbox_key(state: ExecutionTeamState, session_id: str) -> str:
        return f"agentscope:execution-team-inbox:{_safe_component(state.context.tenant_id)}:{_safe_component(state.team_id)}:{_safe_component(session_id)}"


def _safe_component(value: str) -> str:
    """Keep tenant-controlled identifiers safe and unambiguous in bus keys."""
    return re.sub(r"[^A-Za-z0-9_.:-]", "_", str(value))[:160] or "empty"


__all__ = [
    "ActiveTenantRequired",
    "AgentDefinitionUnavailable",
    "AgentScopeExecutionTeamCoordinator",
    "EnabledAgentDefinitionResolver",
    "ExecutionTeamContext",
    "ExecutionTeamError",
    "ExecutionTeamExists",
    "ExecutionTeamState",
    "ExecutionWorker",
    "MAX_WORKERS",
    "NestedTeamNotAllowed",
    "NotTeamLeader",
    "TeamReconnect",
    "WorkerLimitExceeded",
]
{%- else %}
"""Execution teams are not configured."""
{%- endif %}
