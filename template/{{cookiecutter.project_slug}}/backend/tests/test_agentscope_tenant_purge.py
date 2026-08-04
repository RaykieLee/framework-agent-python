{%- if cookiecutter.use_agentscope and cookiecutter.enable_teams and cookiecutter.use_jwt %}
"""Contract tests for tenant-scoped asynchronous purge."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.services.agentscope_tenant_purge import (
    AllowTenantPurgeAuthorizer,
    InMemoryPurgeAuditSink,
    InMemoryPurgeJobStore,
    InMemoryPurgeQueue,
    PurgeStatus,
    PurgeStore,
    TenantPurgeIncomplete,
    TenantPurgeNotFound,
    TenantPurgeRequest,
    TenantPurgeService,
)


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


class RecordingStore:
    """Fake physical store that deletes only records for the passed Tenant."""

    def __init__(self, store: PurgeStore, *, fail_once: bool = False) -> None:
        self.store = store
        self.records = {"tenant-a:record", "tenant-b:record"}
        self.calls: list[str] = []
        self.fail_once = fail_once

    async def purge_tenant(self, tenant_id: str) -> int:
        self.calls.append(tenant_id)
        if self.fail_once:
            self.fail_once = False
            raise RuntimeError("temporary store outage")
        owned = {item for item in self.records if item.startswith(f"{tenant_id}:")}
        self.records.difference_update(owned)
        return len(owned)


def _request(
    request_id: str = "request-1", confirmation: str = "PURGE tenant-a"
) -> TenantPurgeRequest:
    return TenantPurgeRequest(
        tenant_id="tenant-a",
        actor_user_id="owner-a",
        request_id=request_id,
        confirmation=confirmation,
    )


def _service(
    stores: tuple[RecordingStore, ...],
) -> tuple[TenantPurgeService, InMemoryPurgeJobStore, InMemoryPurgeQueue, InMemoryPurgeAuditSink]:
    jobs = InMemoryPurgeJobStore()
    queue = InMemoryPurgeQueue()
    audit = InMemoryPurgeAuditSink()
    service = TenantPurgeService(
        stores=stores,
        jobs=jobs,
        queue=queue,
        audit=audit,
        authorizer=AllowTenantPurgeAuthorizer(),
        clock=lambda: datetime(2026, 1, 1, tzinfo=UTC),
    )
    return service, jobs, queue, audit


def _stores(*, failing: PurgeStore | None = None) -> tuple[RecordingStore, ...]:
    return tuple(RecordingStore(store, fail_once=store is failing) for store in PurgeStore)


@pytest.mark.anyio
async def test_request_requires_exact_confirmation_and_is_idempotently_queued() -> None:
    service, _jobs, queue, _audit = _service(_stores())

    with pytest.raises(PermissionError):
        await service.request(_request(confirmation="PURGE tenant-b"))

    first = await service.request(_request())
    second = await service.request(_request(request_id="retry-from-client"))

    assert first.job_id == second.job_id
    assert first.status is PurgeStatus.QUEUED
    assert queue.jobs == [first.job_id]


@pytest.mark.anyio
async def test_success_deletes_only_target_tenant_and_preserves_audit_events() -> None:
    stores = _stores()
    service, _jobs, _queue, audit = _service(stores)

    job = await service.request(_request())
    report = await service.run(job.job_id)

    assert report.complete
    assert report.status is PurgeStatus.COMPLETED
    assert set(report.completed_stores) == set(PurgeStore)
    assert all(store.records == {"tenant-b:record"} for store in stores)
    assert all(store.calls == ["tenant-a"] for store in stores)
    assert any(event.event == "completed" and event.store is None for event in audit.events)


@pytest.mark.anyio
async def test_partial_failure_reports_incomplete_and_retry_runs_only_failed_store() -> None:
    failing = PurgeStore.MEM0
    stores = _stores(failing=failing)
    service, _jobs, _queue, _audit = _service(stores)

    job = await service.request(_request())
    with pytest.raises(TenantPurgeIncomplete) as error:
        await service.run(job.job_id)
    assert error.value.report.status is PurgeStatus.FAILED
    assert error.value.report.failed_stores == (failing,)
    assert job.failed_stores == {failing: "RuntimeError"}

    await service.run(job.job_id)
    assert job.status is PurgeStatus.COMPLETED
    assert stores[list(PurgeStore).index(failing)].calls == ["tenant-a", "tenant-a"]
    for store in stores:
        if store.store is not failing:
            assert store.calls == ["tenant-a"]


@pytest.mark.anyio
async def test_status_rejects_a_job_from_another_tenant() -> None:
    service, _jobs, _queue, _audit = _service(_stores())
    job = await service.request(_request())

    with pytest.raises(TenantPurgeNotFound):
        await service.status(tenant_id="tenant-b", job_id=job.job_id)


{%- else %}
"""AgentScope Tenant purge tests are not configured."""
{%- endif %}
