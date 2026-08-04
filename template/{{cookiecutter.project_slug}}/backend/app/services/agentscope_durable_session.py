{%- if cookiecutter.use_agentscope %}
"""Durable AgentScope session state.

The execution runtime owns the native AgentScope object, while this module owns
the durable *identity* around it.  The seam deliberately depends on small async
protocols so generated applications can use PostgreSQL and Redis in production
and the same behavior can be tested in-process without either service.
"""

from __future__ import annotations

import asyncio
import contextlib
import hashlib
import time
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable, Coroutine, Mapping
from dataclasses import dataclass, field
from typing import Any, Protocol


class SessionOwnershipError(PermissionError):
    """Raised when a tenant attempts to use another tenant's session."""


class RequestInProgress(RuntimeError):
    """Raised when a request is being processed by another worker."""


class RequestCancelled(asyncio.CancelledError):
    """Raised when a durable request has been cancelled."""


@dataclass(frozen=True, slots=True)
class AgentScopeSessionRef:
    """Stable mapping between a Control Plane conversation and AgentScope."""

    tenant_id: str
    conversation_id: str
    agent_session_id: str


@dataclass(frozen=True, slots=True)
class BufferedEvent:
    """A replayable product event emitted by an AgentScope turn."""

    event_id: str
    request_id: str
    name: str
    payload: Mapping[str, Any]
    sequence: int
    delivered: bool = False


@dataclass(frozen=True, slots=True)
class RequestResult:
    """Idempotent result for one client request."""

    request_id: str
    content: str
    message_id: str | None = None
    charged: bool = False


@dataclass(slots=True)
class CancellationToken:
    """Cooperative cancellation state shared by a running request."""

    _cancelled: asyncio.Event = field(default_factory=asyncio.Event, repr=False)

    def cancel(self) -> None:
        self._cancelled.set()

    @property
    def cancelled(self) -> bool:
        return self._cancelled.is_set()

    async def raise_if_cancelled(self) -> None:
        if self.cancelled:
            raise RequestCancelled()


class DurableSessionStore(Protocol):
    """Persistence boundary implemented by PostgreSQL + Redis in production."""

    async def get_or_create_mapping(
        self, *, tenant_id: str, conversation_id: str
    ) -> AgentScopeSessionRef: ...

    async def get_request(self, key: str, request_id: str) -> RequestResult | None: ...

    async def put_request(self, key: str, result: RequestResult) -> None: ...

    async def append_event(self, key: str, event: BufferedEvent) -> None: ...

    async def claim_events(self, key: str, *, after_sequence: int = 0) -> list[BufferedEvent]: ...

    async def acknowledge_events(self, key: str, event_ids: list[str]) -> None: ...

    def request_lock(self, key: str) -> contextlib.AbstractAsyncContextManager[None]: ...

    async def mark_cancelled(self, key: str, request_id: str) -> None: ...

    async def is_cancelled(self, key: str, request_id: str) -> bool: ...


class PostgresSessionRepository(Protocol):
    """Control-plane persistence required by the production store adapter."""

    async def get_or_create_agentscope_mapping(
        self, *, tenant_id: str, conversation_id: str
    ) -> AgentScopeSessionRef: ...

    async def get_request_result(self, *, key: str, request_id: str) -> RequestResult | None: ...

    async def save_request_result(self, *, key: str, result: RequestResult) -> None: ...

    async def append_event(self, *, key: str, event: BufferedEvent) -> None: ...
    async def list_pending_events(self, *, key: str, after_sequence: int) -> list[BufferedEvent]: ...

    async def acknowledge_events(self, *, key: str, event_ids: list[str]) -> None: ...


class InMemoryDurableSessionStore:
    """Behaviorally complete test double for the durable store seam."""

    def __init__(self) -> None:
        self.mappings: dict[str, AgentScopeSessionRef] = {}
        self.requests: dict[tuple[str, str], RequestResult] = {}
        self.events: dict[str, list[BufferedEvent]] = {}
        self.cancelled: set[tuple[str, str]] = set()
        self._locks: dict[str, asyncio.Lock] = {}
        self._sequence = 0

    async def get_or_create_mapping(
        self, *, tenant_id: str, conversation_id: str
    ) -> AgentScopeSessionRef:
        key = mapping_key(tenant_id, conversation_id)
        existing = self.mappings.get(key)
        if existing is not None:
            return existing
        ref = AgentScopeSessionRef(
            tenant_id=tenant_id,
            conversation_id=conversation_id,
            agent_session_id=str(uuid.uuid4()),
        )
        self.mappings[key] = ref
        return ref

    async def get_request(self, key: str, request_id: str) -> RequestResult | None:
        return self.requests.get((key, request_id))

    async def put_request(self, key: str, result: RequestResult) -> None:
        self.requests.setdefault((key, result.request_id), result)

    async def append_event(self, key: str, event: BufferedEvent) -> None:
        bucket = self.events.setdefault(key, [])
        if any(item.event_id == event.event_id for item in bucket):
            return
        bucket.append(event)

    async def claim_events(self, key: str, *, after_sequence: int = 0) -> list[BufferedEvent]:
        pending = [
            event
            for event in self.events.get(key, [])
            if event.sequence > after_sequence and not event.delivered
        ]
        # Claiming is atomic under the session lock in the production adapter.
        # Marking here makes a second reconnect unable to replay the same event.
        ids = {event.event_id for event in pending}
        if ids:
            await self.acknowledge_events(key, list(ids))
        return pending

    async def acknowledge_events(self, key: str, event_ids: list[str]) -> None:
        ids = set(event_ids)
        self.events[key] = [
            BufferedEvent(
                event_id=event.event_id,
                request_id=event.request_id,
                name=event.name,
                payload=event.payload,
                sequence=event.sequence,
                delivered=True if event.event_id in ids else event.delivered,
            )
            for event in self.events.get(key, [])
        ]

    @contextlib.asynccontextmanager
    async def request_lock(self, key: str) -> AsyncIterator[None]:
        lock = self._locks.setdefault(key, asyncio.Lock())
        async with lock:
            yield

    async def mark_cancelled(self, key: str, request_id: str) -> None:
        self.cancelled.add((key, request_id))

    async def is_cancelled(self, key: str, request_id: str) -> bool:
        return (key, request_id) in self.cancelled

    def next_sequence(self) -> int:
        self._sequence += 1
        return self._sequence


class RedisPostgresDurableSessionStore:
    """Production adapter: PostgreSQL records plus Redis distributed locks.

    The repository owns SQL transactions/unique constraints. Redis is used only
    for short-lived coordination and cancellation flags, so a process restart
    cannot lose the conversation-to-AgentScope mapping or request result.
    """

    def __init__(self, repository: PostgresSessionRepository, redis: Any) -> None:
        self.repository = repository
        self.redis = redis

    async def get_or_create_mapping(
        self, *, tenant_id: str, conversation_id: str
    ) -> AgentScopeSessionRef:
        return await self.repository.get_or_create_agentscope_mapping(
            tenant_id=tenant_id,
            conversation_id=conversation_id,
        )

    async def get_request(self, key: str, request_id: str) -> RequestResult | None:
        return await self.repository.get_request_result(key=key, request_id=request_id)

    async def put_request(self, key: str, result: RequestResult) -> None:
        await self.repository.save_request_result(key=key, result=result)

    async def append_event(self, key: str, event: BufferedEvent) -> None:
        await self.repository.append_event(key=key, event=event)

    async def claim_events(self, key: str, *, after_sequence: int = 0) -> list[BufferedEvent]:
        return await self.repository.list_pending_events(key=key, after_sequence=after_sequence)

    async def acknowledge_events(self, key: str, event_ids: list[str]) -> None:
        await self.repository.acknowledge_events(key=key, event_ids=event_ids)

    @contextlib.asynccontextmanager
    async def request_lock(self, key: str) -> AsyncIterator[None]:
        # redis-py Lock uses a token and safely releases only the owner token.
        lock = self.redis.lock(f"{key}:lock", timeout=120, blocking_timeout=30)
        acquired = await lock.acquire()
        if not acquired:
            raise RequestInProgress("Another process owns this AgentScope request lock")
        try:
            yield
        finally:
            with contextlib.suppress(Exception):
                await lock.release()

    async def mark_cancelled(self, key: str, request_id: str) -> None:
        await self.redis.set(f"{key}:cancel:{request_id}", "1", ex=3600)

    async def is_cancelled(self, key: str, request_id: str) -> bool:
        return bool(await self.redis.exists(f"{key}:cancel:{request_id}"))


def _safe_component(value: str) -> str:
    """Keep a readable tenant prefix while preventing key collisions."""
    raw = "".join(char if char.isalnum() or char in "._-" else "_" for char in str(value))
    digest = hashlib.sha256(str(value).encode("utf-8")).hexdigest()[:16]
    return f"{raw[:48] or 'empty'}-{digest}"


def mapping_key(tenant_id: str, conversation_id: str) -> str:
    return f"agentscope:tenant:{_safe_component(tenant_id)}:conversation:{_safe_component(conversation_id)}:mapping"


def session_key(ref: AgentScopeSessionRef) -> str:
    return f"agentscope:tenant:{_safe_component(ref.tenant_id)}:conversation:{_safe_component(ref.conversation_id)}:session"


def request_key(ref: AgentScopeSessionRef) -> str:
    return f"{session_key(ref)}:requests"


def event_key(ref: AgentScopeSessionRef) -> str:
    return f"{session_key(ref)}:events"


Runner = Callable[[CancellationToken], Coroutine[Any, Any, RequestResult | str]]
Charge = Callable[[str], Awaitable[None]]


class AgentScopeDurableSession:
    """Process-safe request coordinator around one AgentScope conversation."""

    def __init__(
        self,
        store: DurableSessionStore,
        *,
        tenant_id: str,
        conversation_id: str,
    ) -> None:
        self.store = store
        self.tenant_id = str(tenant_id)
        self.conversation_id = str(conversation_id)
        self.ref: AgentScopeSessionRef | None = None

    async def open(self) -> AgentScopeSessionRef:
        """Load the same AgentScope session after reconnect/process restart."""
        ref = await self.store.get_or_create_mapping(
            tenant_id=self.tenant_id,
            conversation_id=self.conversation_id,
        )
        if ref.tenant_id != self.tenant_id:
            raise SessionOwnershipError("Session belongs to another tenant")
        self.ref = ref
        return ref

    async def execute(
        self,
        request_id: str,
        runner: Runner,
        *,
        charge: Charge | None = None,
    ) -> RequestResult:
        """Run one request exactly once, including billing/message persistence."""
        ref = self.ref or await self.open()
        if not request_id:
            raise ValueError("request_id is required for idempotent execution")
        key = request_key(ref)
        async with self.store.request_lock(key):
            existing = await self.store.get_request(key, request_id)
            if existing is not None:
                return existing
            if await self.store.is_cancelled(key, request_id):
                raise RequestCancelled()
            token = CancellationToken()
            run_task = asyncio.create_task(runner(token))
            cancel_task = asyncio.create_task(self._watch_cancellation(key, request_id, token))
            try:
                raw = await run_task
                if isinstance(raw, RequestResult):
                    result = raw if raw.request_id == request_id else RequestResult(
                        request_id=request_id,
                        content=raw.content,
                        message_id=raw.message_id,
                        charged=raw.charged,
                    )
                else:
                    result = RequestResult(request_id=request_id, content=str(raw))
                await token.raise_if_cancelled()
                if charge is not None and not result.charged:
                    await charge(request_id)
                    result = RequestResult(
                        request_id=result.request_id,
                        content=result.content,
                        message_id=result.message_id,
                        charged=True,
                    )
                await self.store.put_request(key, result)
                await self.emit(request_id, "complete", {"content": result.content})
                return result
            except asyncio.CancelledError:
                token.cancel()
                run_task.cancel()
                raise
            finally:
                cancel_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await cancel_task

    async def _watch_cancellation(
        self, key: str, request_id: str, token: CancellationToken
    ) -> None:
        """Propagate a Redis cancellation flag to a cooperative runner."""
        while not token.cancelled:
            if await self.store.is_cancelled(key, request_id):
                token.cancel()
                return
            await asyncio.sleep(0.05)

    async def result(self, request_id: str) -> RequestResult | None:
        """Read a completed request without executing it again."""
        ref = self.ref or await self.open()
        return await self.store.get_request(request_key(ref), request_id)

    async def cancel(self, request_id: str) -> None:
        ref = self.ref or await self.open()
        await self.store.mark_cancelled(request_key(ref), request_id)

    async def emit(self, request_id: str, name: str, payload: Mapping[str, Any]) -> BufferedEvent:
        ref = self.ref or await self.open()
        if not request_id:
            raise ValueError("request_id is required for replayable events")
        sequence = getattr(self.store, "next_sequence", lambda: int(time.time_ns()))()
        event = BufferedEvent(
            event_id=f"{request_id}:{sequence}:{uuid.uuid4().hex[:8]}",
            request_id=request_id,
            name=name,
            payload=dict(payload),
            sequence=sequence,
        )
        await self.store.append_event(event_key(ref), event)
        return event

    async def replay(self, *, after_sequence: int = 0) -> list[BufferedEvent]:
        """Claim undelivered events under the cross-process replay lock."""
        ref = self.ref or await self.open()
        async with self.store.request_lock(event_key(ref)):
            return await self.store.claim_events(event_key(ref), after_sequence=after_sequence)

    async def acknowledge(self, events: list[BufferedEvent]) -> None:
        ref = self.ref or await self.open()
        async with self.store.request_lock(event_key(ref)):
            await self.store.acknowledge_events(
                event_key(ref), [event.event_id for event in events]
            )


# A short alias keeps application imports readable while preserving the explicit
# AgentScope name for integration tests and future runtime adapters.
DurableAgentSession = AgentScopeDurableSession

__all__ = [
    "AgentScopeDurableSession",
    "AgentScopeSessionRef",
    "BufferedEvent",
    "CancellationToken",
    "DurableAgentSession",
    "DurableSessionStore",
    "InMemoryDurableSessionStore",
    "PostgresSessionRepository",
    "RedisPostgresDurableSessionStore",
    "RequestCancelled",
    "RequestInProgress",
    "RequestResult",
    "SessionOwnershipError",
    "event_key",
    "mapping_key",
    "request_key",
    "session_key",
]
{%- else %}
"""Durable AgentScope sessions are not configured."""
{%- endif %}
