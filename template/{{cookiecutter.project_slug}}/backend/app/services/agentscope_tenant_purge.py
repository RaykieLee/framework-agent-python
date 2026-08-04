{%- if cookiecutter.use_agentscope and cookiecutter.enable_teams and cookiecutter.use_jwt %}
"""Auditable, tenant-scoped deletion for AgentScope state.

The Control Plane owns the purge job and its authorization.  Physical stores
are deliberately represented by small adapters so PostgreSQL, Redis, Qdrant,
Mem0, workspace storage, and encrypted connection stores can be wired by the
deployment without importing AgentScope internals.  A worker calls
``TenantPurgeService.run`` after the API has queued the job.

No adapter receives a user supplied key, collection, or path.  It receives
only the immutable tenant identifier, and the PostgreSQL adapter is always
called with ``preserve_audit=True``.  This makes the tenant boundary explicit
and prevents a purge from deleting the append-only audit trail.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import AsyncIterator, Awaitable, Callable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Protocol
from uuid import uuid4

from app.core.exceptions import AppException, ExternalServiceError

logger = logging.getLogger(__name__)


class TenantPurgeError(RuntimeError):
    """Base class for purge lifecycle failures."""


class TenantPurgeAuthorizationError(TenantPurgeError, PermissionError):
    """Raised when a caller cannot delete the requested Tenant."""


class TenantPurgeNotFound(TenantPurgeError):
    """Raised when a product-safe status lookup cannot find a job."""


class TenantPurgeIncomplete(TenantPurgeError):
    """Raised when one or more stores still need a retry."""

    def __init__(self, report: "TenantPurgeReport") -> None:
        self.report = report
        stores = ", ".join(item.value for item in report.failed_stores)
        super().__init__(f"tenant purge is incomplete; retry failed stores: {stores}")


class TenantPurgeIntegrationNotConfigured(AppException):
    """The generated API has not been wired to production purge adapters."""

    message = "Tenant purge integration is not configured"
    code = "TENANT_PURGE_NOT_CONFIGURED"
    status_code = 503


class PurgeStore(StrEnum):
    """Physical stores whose tenant-owned state must be removed."""

    CONTROL_PLANE_SQL = "control_plane_sql"
    AGENTSCOPE_SQL = "agentscope_sql"
    REDIS = "redis"
    QDRANT = "qdrant"
    MEM0 = "mem0"
    WORKSPACE = "workspace"
    PERSONAL_CONNECTIONS = "personal_connections"


class PurgeStatus(StrEnum):
    """Public lifecycle state of an asynchronous purge job."""

    QUEUED = "queued"
    RUNNING = "running"
    RETRYING = "retrying"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class TenantPurgeRequest:
    """Authorized deletion intent and idempotency key."""

    tenant_id: str
    actor_user_id: str
    request_id: str
    confirmation: str

    def __post_init__(self) -> None:
        for name in ("tenant_id", "actor_user_id", "request_id", "confirmation"):
            if not str(getattr(self, name)).strip():
                raise ValueError(f"{name} is required for a Tenant purge")

    @property
    def operation_id(self) -> str:
        """One purge operation per Tenant, regardless of request retries."""
        return f"tenant-purge:{self.tenant_id}"


@dataclass(frozen=True, slots=True)
class PurgeAuditEvent:
    """Append-only transition emitted for operators and compliance tooling."""

    operation_id: str
    job_id: str
    tenant_id: str
    actor_user_id: str
    store: PurgeStore | None
    event: str
    occurred_at: datetime
    details: Mapping[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class TenantPurgeJob:
    """Durable job projection used by the queue and status API."""

    job_id: str
    operation_id: str
    tenant_id: str
    actor_user_id: str
    request_id: str
    status: PurgeStatus = PurgeStatus.QUEUED
    completed_stores: set[PurgeStore] = field(default_factory=set)
    failed_stores: dict[PurgeStore, str] = field(default_factory=dict)
    attempts: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    finished_at: datetime | None = None

    @property
    def complete(self) -> bool:
        return self.status is PurgeStatus.COMPLETED

    @property
    def can_retry(self) -> bool:
        return self.status is PurgeStatus.FAILED and bool(self.failed_stores)

    def public(self) -> dict[str, Any]:
        """Return a redaction-safe representation (never adapter errors)."""
        return {
            "job_id": self.job_id,
            "tenant_id": self.tenant_id,
            "status": self.status.value,
            "completed_stores": sorted(item.value for item in self.completed_stores),
            "failed_stores": sorted(item.value for item in self.failed_stores),
            "attempts": self.attempts,
            "can_retry": self.can_retry,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "finished_at": self.finished_at,
        }


@dataclass(frozen=True, slots=True)
class TenantPurgeReport:
    """Observable result of one worker attempt."""

    job_id: str
    tenant_id: str
    status: PurgeStatus
    completed_stores: tuple[PurgeStore, ...]
    failed_stores: tuple[PurgeStore, ...]
    attempts: int

    @property
    def complete(self) -> bool:
        return self.status is PurgeStatus.COMPLETED


class TenantPurgeAuthorizer(Protocol):
    """Control-plane seam for owner confirmation and deletion policy."""

    async def authorize(self, request: TenantPurgeRequest) -> None: ...


class PurgeStoreAdapter(Protocol):
    """Tenant-scoped deletion boundary for one physical store."""

    store: PurgeStore

    async def purge_tenant(self, tenant_id: str) -> int: ...


class PurgeJobStore(Protocol):
    """Durable PostgreSQL job/ledger seam used by production workers."""

    async def get_or_create(self, request: TenantPurgeRequest) -> TenantPurgeJob: ...

    async def get(self, job_id: str) -> TenantPurgeJob | None: ...

    async def save(self, job: TenantPurgeJob) -> None: ...

    def lock(self, operation_id: str) -> contextlib.AbstractAsyncContextManager[None]: ...


class PurgeQueue(Protocol):
    """Async queue boundary (Taskiq/Celery/ARQ in production)."""

    async def enqueue(self, job: TenantPurgeJob) -> None: ...


class AuditSink(Protocol):
    """Append-only SQL audit boundary; purge never calls delete on it."""

    async def append(self, event: PurgeAuditEvent) -> None: ...


class AllowTenantPurgeAuthorizer:
    """Explicit local/test authorizer for callers that already checked RBAC."""

    async def authorize(self, request: TenantPurgeRequest) -> None:
        expected = f"PURGE {request.tenant_id}"
        if request.confirmation != expected:
            raise TenantPurgeAuthorizationError(
                "Tenant purge confirmation must exactly match the tenant identifier"
            )


class InMemoryPurgeJobStore:
    """Behaviorally complete test double for the durable job ledger."""

    def __init__(self) -> None:
        self.jobs: dict[str, TenantPurgeJob] = {}
        self.by_operation: dict[str, str] = {}
        self._locks: dict[str, asyncio.Lock] = {}

    async def get_or_create(self, request: TenantPurgeRequest) -> TenantPurgeJob:
        existing_id = self.by_operation.get(request.operation_id)
        if existing_id is not None:
            return self.jobs[existing_id]
        now = datetime.now(UTC)
        job = TenantPurgeJob(
            job_id=f"purge-{uuid4().hex}",
            operation_id=request.operation_id,
            tenant_id=request.tenant_id,
            actor_user_id=request.actor_user_id,
            request_id=request.request_id,
            created_at=now,
            updated_at=now,
        )
        self.jobs[job.job_id] = job
        self.by_operation[job.operation_id] = job.job_id
        return job

    async def get(self, job_id: str) -> TenantPurgeJob | None:
        return self.jobs.get(job_id)

    async def save(self, job: TenantPurgeJob) -> None:
        job.updated_at = datetime.now(UTC)
        self.jobs[job.job_id] = job

    @contextlib.asynccontextmanager
    async def lock(self, operation_id: str) -> AsyncIterator[None]:
        lock = self._locks.setdefault(operation_id, asyncio.Lock())
        async with lock:
            yield


class InMemoryPurgeQueue:
    """Queue fake that records jobs without running destructive work."""

    def __init__(self) -> None:
        self.jobs: list[str] = []

    async def enqueue(self, job: TenantPurgeJob) -> None:
        if job.job_id not in self.jobs:
            self.jobs.append(job.job_id)


class InMemoryPurgeAuditSink:
    """Append-only audit fake useful for unit and isolation assertions."""

    def __init__(self) -> None:
        self.events: list[PurgeAuditEvent] = []

    async def append(self, event: PurgeAuditEvent) -> None:
        self.events.append(event)


class _CallbackPurgeStore:
    def __init__(self, store: PurgeStore, callback: Callable[[str], Awaitable[int]]) -> None:
        self.store = store
        self._callback = callback

    async def purge_tenant(self, tenant_id: str) -> int:
        if not tenant_id.strip():
            raise ValueError("tenant_id is required")
        return int(await self._callback(tenant_id))


class PostgresControlPlanePurgeRepository(Protocol):
    async def delete_tenant_records(self, tenant_id: str, *, preserve_audit: bool) -> int: ...


class AgentScopeSqlPurgeRepository(Protocol):
    async def delete_tenant_state(self, tenant_id: str) -> int: ...


class RedisPurgeRepository(Protocol):
    async def delete_tenant_keys(self, tenant_id: str) -> int: ...


class QdrantPurgeRepository(Protocol):
    async def delete_tenant_vectors(self, tenant_id: str) -> int: ...


class Mem0PurgeRepository(Protocol):
    async def delete_tenant_memories(self, tenant_id: str) -> int: ...


class WorkspacePurgeRepository(Protocol):
    async def delete_tenant_workspace(self, tenant_id: str) -> int: ...


class PersonalConnectionPurgeRepository(Protocol):
    async def delete_tenant_connections(self, tenant_id: str) -> int: ...


@dataclass(frozen=True, slots=True)
class ProductionTenantPurgeAdapters:
    """Explicit infrastructure wiring contract for a production deployment."""

    control_plane: PostgresControlPlanePurgeRepository
    agentscope_sql: AgentScopeSqlPurgeRepository
    redis: RedisPurgeRepository
    qdrant: QdrantPurgeRepository
    mem0: Mem0PurgeRepository
    workspace: WorkspacePurgeRepository
    personal_connections: PersonalConnectionPurgeRepository


def build_production_purge_stores(
    adapters: ProductionTenantPurgeAdapters,
) -> tuple[PurgeStoreAdapter, ...]:
    """Bind repository callbacks while retaining one tenant-only argument."""
    return (
        _CallbackPurgeStore(
            PurgeStore.CONTROL_PLANE_SQL,
            lambda tenant_id: adapters.control_plane.delete_tenant_records(
                tenant_id, preserve_audit=True
            ),
        ),
        _CallbackPurgeStore(
            PurgeStore.AGENTSCOPE_SQL,
            adapters.agentscope_sql.delete_tenant_state,
        ),
        _CallbackPurgeStore(PurgeStore.REDIS, adapters.redis.delete_tenant_keys),
        _CallbackPurgeStore(PurgeStore.QDRANT, adapters.qdrant.delete_tenant_vectors),
        _CallbackPurgeStore(PurgeStore.MEM0, adapters.mem0.delete_tenant_memories),
        _CallbackPurgeStore(PurgeStore.WORKSPACE, adapters.workspace.delete_tenant_workspace),
        _CallbackPurgeStore(
            PurgeStore.PERSONAL_CONNECTIONS,
            adapters.personal_connections.delete_tenant_connections,
        ),
    )


class TenantPurgeService:
    """Queue and execute an idempotent, retryable purge for one Tenant."""

    def __init__(
        self,
        *,
        stores: tuple[PurgeStoreAdapter, ...],
        jobs: PurgeJobStore,
        queue: PurgeQueue,
        audit: AuditSink,
        authorizer: TenantPurgeAuthorizer,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        expected = tuple(PurgeStore)
        provided = tuple(item.store for item in stores)
        if provided != expected:
            raise ValueError(
                "Tenant purge stores must include each physical store exactly once "
                f"in order: {[item.value for item in expected]}"
            )
        self.stores = stores
        self.jobs = jobs
        self.queue = queue
        self.audit = audit
        self.authorizer = authorizer
        self.clock = clock or (lambda: datetime.now(UTC))

    async def request(self, request: TenantPurgeRequest) -> TenantPurgeJob:
        """Authorize, persist, and enqueue one idempotent purge job."""
        await self.authorizer.authorize(request)
        async with self.jobs.lock(request.operation_id):
            job = await self.jobs.get_or_create(request)
            if job.status is PurgeStatus.COMPLETED:
                return job
            await self.queue.enqueue(job)
            await self._emit(request, job, None, "queued")
            return job

    async def run(self, job_id: str) -> TenantPurgeReport:
        """Run pending stores; raise an incomplete report when retry is needed."""
        job = await self.jobs.get(job_id)
        if job is None:
            raise TenantPurgeNotFound(f"Tenant purge job not found: {job_id}")
        async with self.jobs.lock(job.operation_id):
            job = await self.jobs.get(job_id)
            if job is None:
                raise TenantPurgeNotFound(f"Tenant purge job not found: {job_id}")
            if job.status is PurgeStatus.COMPLETED:
                return self._report(job)

            job.attempts += 1
            job.status = PurgeStatus.RETRYING if job.failed_stores else PurgeStatus.RUNNING
            await self.jobs.save(job)
            await self._emit_for_job(job, None, "started")

            for adapter in self.stores:
                if adapter.store in job.completed_stores:
                    continue
                await self._emit_for_job(job, adapter.store, "started")
                try:
                    count = await adapter.purge_tenant(job.tenant_id)
                except Exception as exc:  # noqa: BLE001 - report each independent store
                    job.failed_stores[adapter.store] = type(exc).__name__
                    await self._emit_for_job(
                        job, adapter.store, "failed", error=type(exc).__name__
                    )
                    logger.warning(
                        "Tenant purge store failed job=%s tenant=%s store=%s",
                        job.job_id,
                        job.tenant_id,
                        adapter.store.value,
                        exc_info=True,
                    )
                else:
                    job.completed_stores.add(adapter.store)
                    job.failed_stores.pop(adapter.store, None)
                    await self._emit_for_job(job, adapter.store, "completed", deleted=count)
                await self.jobs.save(job)

            if job.failed_stores:
                job.status = PurgeStatus.FAILED
                await self._emit_for_job(
                    job, None, "incomplete", failed=sorted(item.value for item in job.failed_stores)
                )
                await self.jobs.save(job)
                raise TenantPurgeIncomplete(self._report(job))

            job.status = PurgeStatus.COMPLETED
            job.finished_at = self.clock()
            await self.jobs.save(job)
            await self._emit_for_job(job, None, "completed")
            return self._report(job)

    async def status(self, *, tenant_id: str, job_id: str) -> TenantPurgeJob:
        """Read a job only when its immutable Tenant matches the caller scope."""
        job = await self.jobs.get(job_id)
        if job is None or job.tenant_id != tenant_id:
            raise TenantPurgeNotFound("Tenant purge job not found")
        return job

    async def _emit(
        self,
        request: TenantPurgeRequest,
        job: TenantPurgeJob,
        store: PurgeStore | None,
        event: str,
        **details: Any,
    ) -> None:
        await self._emit_event(
            PurgeAuditEvent(
                operation_id=request.operation_id,
                job_id=job.job_id,
                tenant_id=request.tenant_id,
                actor_user_id=request.actor_user_id,
                store=store,
                event=event,
                occurred_at=self.clock(),
                details=details,
            )
        )

    async def _emit_for_job(
        self,
        job: TenantPurgeJob,
        store: PurgeStore | None,
        event: str,
        **details: Any,
    ) -> None:
        await self._emit_event(
            PurgeAuditEvent(
                operation_id=job.operation_id,
                job_id=job.job_id,
                tenant_id=job.tenant_id,
                actor_user_id=job.actor_user_id,
                store=store,
                event=event,
                occurred_at=self.clock(),
                details=details,
            )
        )

    async def _emit_event(self, event: PurgeAuditEvent) -> None:
        try:
            await self.audit.append(event)
        except Exception:  # noqa: BLE001 - audit failure never leaks payloads
            logger.exception(
                "Tenant purge audit sink failed operation=%s event=%s",
                event.operation_id,
                event.event,
            )

    @staticmethod
    def _report(job: TenantPurgeJob) -> TenantPurgeReport:
        return TenantPurgeReport(
            job_id=job.job_id,
            tenant_id=job.tenant_id,
            status=job.status,
            completed_stores=tuple(item for item in PurgeStore if item in job.completed_stores),
            failed_stores=tuple(item for item in PurgeStore if item in job.failed_stores),
            attempts=job.attempts,
        )


_configured_service: TenantPurgeService | None = None


def configure_tenant_purge_service(service: TenantPurgeService) -> None:
    """Integration hook for wiring SQL/Redis/queue adapters at application boot."""
    global _configured_service
    _configured_service = service


def get_configured_tenant_purge_service() -> TenantPurgeService:
    """Return the configured service or a product-safe 503 error."""
    if _configured_service is None:
        raise TenantPurgeIntegrationNotConfigured()
    return _configured_service


__all__ = [
    "AgentScopeSqlPurgeRepository",
    "AllowTenantPurgeAuthorizer",
    "AuditSink",
    "InMemoryPurgeAuditSink",
    "InMemoryPurgeJobStore",
    "InMemoryPurgeQueue",
    "Mem0PurgeRepository",
    "PersonalConnectionPurgeRepository",
    "PostgresControlPlanePurgeRepository",
    "ProductionTenantPurgeAdapters",
    "PurgeAuditEvent",
    "PurgeJobStore",
    "PurgeQueue",
    "PurgeStatus",
    "PurgeStore",
    "PurgeStoreAdapter",
    "QdrantPurgeRepository",
    "RedisPurgeRepository",
    "TenantPurgeAuthorizer",
    "TenantPurgeError",
    "TenantPurgeIncomplete",
    "TenantPurgeIntegrationNotConfigured",
    "TenantPurgeJob",
    "TenantPurgeNotFound",
    "TenantPurgeReport",
    "TenantPurgeRequest",
    "TenantPurgeService",
    "WorkspacePurgeRepository",
    "build_production_purge_stores",
    "configure_tenant_purge_service",
    "get_configured_tenant_purge_service",
]
{%- else %}
"""AgentScope Tenant purge is not configured."""
{%- endif %}
