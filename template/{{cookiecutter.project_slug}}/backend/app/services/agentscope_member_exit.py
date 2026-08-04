{%- if cookiecutter.use_agentscope and cookiecutter.enable_teams %}
"""Idempotent private-state cleanup when a member leaves a Tenant.

The Control Plane owns membership and authorization.  This module is the
life-cycle boundary that is called after access is revoked; it coordinates
the external stores without importing AgentScope implementation details.
Production applications inject PostgreSQL, Redis, Qdrant/Mem0, and workspace
adapters.  The in-memory implementations below are intentionally complete
fakes for unit tests and local development.
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

logger = logging.getLogger(__name__)


class MemberExitError(RuntimeError):
    """Base error for member-exit lifecycle failures."""


class MemberExitAuthorizationError(MemberExitError, PermissionError):
    """Raised when a former member attempts to use retained Tenant state."""


class MemberExitCleanupIncomplete(MemberExitError):
    """Raised when one or more private-state cleanup steps need a retry."""

    def __init__(self, report: "MemberExitCleanupReport") -> None:
        self.report = report
        failed = ", ".join(step.value for step in report.failed_steps)
        super().__init__(f"member exit cleanup is incomplete; retry failed steps: {failed}")


class CleanupStep(StrEnum):
    """Private resources removed by the member-exit workflow."""

    ACCESS = "access"
    PERSONAL_CONNECTIONS = "personal_connections"
    USER_MEMORY = "user_memory"
    SESSIONS = "sessions"
    EXECUTION_TEAMS = "execution_teams"
    WORKSPACES = "workspaces"


@dataclass(frozen=True, slots=True)
class MemberExitRequest:
    """Control-Plane identity and idempotency key for one member exit."""

    tenant_id: str
    user_id: str
    actor_user_id: str
    request_id: str

    def __post_init__(self) -> None:
        for name in ("tenant_id", "user_id", "actor_user_id", "request_id"):
            if not str(getattr(self, name)).strip():
                raise ValueError(f"{name} is required for member exit cleanup")

    @property
    def operation_id(self) -> str:
        # The target identity, rather than a transient HTTP request, makes a
        # retry from a job or a second process idempotent.
        return f"member-exit:{self.tenant_id}:{self.user_id}"


@dataclass(frozen=True, slots=True)
class CleanupAuditEvent:
    """Append-only event emitted for each cleanup state transition."""

    operation_id: str
    step: CleanupStep
    event: str
    tenant_id: str
    user_id: str
    actor_user_id: str
    request_id: str
    occurred_at: datetime
    details: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class MemberExitCleanupReport:
    """Observable result of one idempotent cleanup attempt."""

    operation_id: str
    tenant_id: str
    user_id: str
    completed_steps: tuple[CleanupStep, ...]
    failed_steps: tuple[CleanupStep, ...]
    tenant_conversations_retained: bool = True

    @property
    def complete(self) -> bool:
        return not self.failed_steps


class MemberExitAuthorizer(Protocol):
    """Optional Control-Plane authorization seam.

    ``MemberService`` performs the normal Owner/Admin checks before invoking
    this workflow.  Queue consumers may inject this protocol to re-check a
    persisted job before it runs.
    """

    async def authorize(self, request: MemberExitRequest) -> None: ...


class MembershipRevoker(Protocol):
    """Revokes membership before any private state is deleted."""

    async def revoke(self, *, tenant_id: str, user_id: str) -> None: ...

    async def is_revoked(self, *, tenant_id: str, user_id: str) -> bool: ...


class PersonalConnectionCleanup(Protocol):
    """PostgreSQL/encrypted-secret boundary for Personal Connections."""

    async def delete_for_member(self, *, tenant_id: str, user_id: str) -> None: ...


class UserMemoryCleanup(Protocol):
    """Mem0/Qdrant boundary for all User Memory namespaces in a Tenant."""

    async def delete_for_member(self, *, tenant_id: str, user_id: str) -> None: ...


class SessionCleanup(Protocol):
    """PostgreSQL session rows and Redis AgentScope session state boundary."""

    async def delete_for_member(self, *, tenant_id: str, user_id: str) -> None: ...


class ExecutionTeamCleanup(Protocol):
    """Redis AgentScope team roster, inbox, event, and run-state boundary."""

    async def delete_for_member(self, *, tenant_id: str, user_id: str) -> None: ...


class WorkspaceCleanup(Protocol):
    """Persistent workspace/artifact storage boundary."""

    async def delete_for_member(self, *, tenant_id: str, user_id: str) -> None: ...


class CleanupLedger(Protocol):
    """Durable idempotency ledger (PostgreSQL in production)."""

    def lock(self, operation_id: str) -> contextlib.AbstractAsyncContextManager[None]: ...

    async def completed(self, operation_id: str) -> set[CleanupStep]: ...

    async def mark_completed(self, operation_id: str, step: CleanupStep) -> None: ...

    async def mark_failed(self, operation_id: str, step: CleanupStep, error: str) -> None: ...


class AuditSink(Protocol):
    """Append-only audit boundary; implementations may use the SQL audit log."""

    async def append(self, event: CleanupAuditEvent) -> None: ...


class TenantConversationAccess:
    """Guard retained Tenant Conversations after a member has departed.

    Conversation rows/messages are never deleted by this ticket.  Every
    read, subscription, execution, and mutation caller can use this guard
    after its normal tenant-membership lookup to make revocation explicit.
    """

    def __init__(self, membership: MembershipRevoker) -> None:
        self.membership = membership

    async def authorize(self, *, tenant_id: str, user_id: str, action: str) -> None:
        if not await self.membership.is_revoked(tenant_id=tenant_id, user_id=user_id):
            return
        raise MemberExitAuthorizationError(
            f"departed member cannot {action} retained Tenant Conversations"
        )


class AllowMemberExitAuthorizer:
    """Explicit test/local authorizer for callers that already checked RBAC."""

    async def authorize(self, request: MemberExitRequest) -> None:
        del request


class InMemoryMembershipRevoker:
    """In-process fake for membership revocation and conversation guards."""

    def __init__(self) -> None:
        self.revoked: set[tuple[str, str]] = set()

    async def revoke(self, *, tenant_id: str, user_id: str) -> None:
        self.revoked.add((tenant_id, user_id))

    async def is_revoked(self, *, tenant_id: str, user_id: str) -> bool:
        return (tenant_id, user_id) in self.revoked


class InMemoryCleanupLedger:
    """Durable-ledger fake that preserves completion across retries."""

    def __init__(self) -> None:
        self.completed_steps: dict[str, set[CleanupStep]] = {}
        self.failures: dict[str, list[tuple[CleanupStep, str]]] = {}
        self._locks: dict[str, asyncio.Lock] = {}

    @contextlib.asynccontextmanager
    async def lock(self, operation_id: str) -> AsyncIterator[None]:
        lock = self._locks.setdefault(operation_id, asyncio.Lock())
        async with lock:
            yield

    async def completed(self, operation_id: str) -> set[CleanupStep]:
        return set(self.completed_steps.get(operation_id, set()))

    async def mark_completed(self, operation_id: str, step: CleanupStep) -> None:
        self.completed_steps.setdefault(operation_id, set()).add(step)

    async def mark_failed(self, operation_id: str, step: CleanupStep, error: str) -> None:
        self.failures.setdefault(operation_id, []).append((step, error))


class InMemoryAuditSink:
    """Append-only audit fake useful for lifecycle assertions."""

    def __init__(self) -> None:
        self.events: list[CleanupAuditEvent] = []

    async def append(self, event: CleanupAuditEvent) -> None:
        self.events.append(event)


class PostgresMemberExitRepository(Protocol):
    """Production PostgreSQL methods needed by member-exit adapters."""

    async def revoke_membership(self, *, tenant_id: str, user_id: str) -> None: ...

    async def delete_personal_connections(self, *, tenant_id: str, user_id: str) -> None: ...

    async def delete_sessions(self, *, tenant_id: str, user_id: str) -> None: ...

    async def load_completed_steps(self, *, operation_id: str) -> set[CleanupStep]: ...

    async def mark_cleanup_step(
        self, *, operation_id: str, step: CleanupStep, error: str | None = None
    ) -> None: ...


class RedisMemberExitRepository(Protocol):
    """Production Redis methods for ephemeral AgentScope state."""

    async def delete_sessions(self, *, tenant_id: str, user_id: str) -> None: ...

    async def delete_execution_teams(self, *, tenant_id: str, user_id: str) -> None: ...


class QdrantMemberExitRepository(Protocol):
    """Production Qdrant/Mem0 namespace deletion boundary."""

    async def delete_user_memory(self, *, tenant_id: str, user_id: str) -> None: ...


class WorkspaceMemberExitRepository(Protocol):
    """Production workspace/object-store deletion boundary."""

    async def delete_workspaces(self, *, tenant_id: str, user_id: str) -> None: ...


@dataclass(frozen=True, slots=True)
class ProductionMemberExitAdapters:
    """Named infrastructure dependencies required by a production app.

    This container is deliberately only a wiring contract.  Concrete SQL,
    Redis, Qdrant, and workspace clients stay outside the generated template,
    while tests can provide small fakes implementing the same protocols.
    """

    postgres: PostgresMemberExitRepository
    redis: RedisMemberExitRepository
    qdrant: QdrantMemberExitRepository
    workspace: WorkspaceMemberExitRepository


class MemberExitCleanupService:
    """Run ordered, retryable private-state cleanup for one departed member."""

    _RESOURCES: tuple[CleanupStep, ...] = (
        CleanupStep.PERSONAL_CONNECTIONS,
        CleanupStep.USER_MEMORY,
        CleanupStep.SESSIONS,
        CleanupStep.EXECUTION_TEAMS,
        CleanupStep.WORKSPACES,
    )

    def __init__(
        self,
        *,
        membership: MembershipRevoker,
        personal_connections: PersonalConnectionCleanup,
        user_memory: UserMemoryCleanup,
        sessions: SessionCleanup,
        execution_teams: ExecutionTeamCleanup,
        workspaces: WorkspaceCleanup,
        ledger: CleanupLedger,
        audit: AuditSink,
        authorizer: MemberExitAuthorizer | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.membership = membership
        self.personal_connections = personal_connections
        self.user_memory = user_memory
        self.sessions = sessions
        self.execution_teams = execution_teams
        self.workspaces = workspaces
        self.ledger = ledger
        self.audit = audit
        self.authorizer = authorizer
        self.clock = clock or (lambda: datetime.now(UTC))

    async def run(self, request: MemberExitRequest) -> MemberExitCleanupReport:
        """Revoke access, then remove each private resource at most once.

        A failed step is recorded and the remaining steps are attempted.  A
        retry skips successful steps and invokes only failed/pending adapters.
        Every adapter must therefore make deletion idempotent in its backing
        store (SQL ``DELETE``, Redis key deletion, Qdrant filter deletion, and
        workspace prefix deletion all naturally support this contract).
        """
        if self.authorizer is not None:
            await self.authorizer.authorize(request)

        async with self.ledger.lock(request.operation_id):
            completed = await self.ledger.completed(request.operation_id)
            failed: list[CleanupStep] = []

            if CleanupStep.ACCESS not in completed:
                try:
                    await self._transition(request, CleanupStep.ACCESS, "started")
                    await self.membership.revoke(tenant_id=request.tenant_id, user_id=request.user_id)
                    await self.ledger.mark_completed(request.operation_id, CleanupStep.ACCESS)
                    completed.add(CleanupStep.ACCESS)
                    await self._transition(request, CleanupStep.ACCESS, "completed")
                except Exception as exc:
                    await self.ledger.mark_failed(request.operation_id, CleanupStep.ACCESS, str(exc))
                    await self._transition(request, CleanupStep.ACCESS, "failed", error=str(exc))
                    report = self._report(request, completed, [CleanupStep.ACCESS])
                    raise MemberExitCleanupIncomplete(report) from exc

            operations: dict[CleanupStep, Callable[[], Awaitable[None]]] = {
                CleanupStep.PERSONAL_CONNECTIONS: lambda: self.personal_connections.delete_for_member(
                    tenant_id=request.tenant_id, user_id=request.user_id
                ),
                CleanupStep.USER_MEMORY: lambda: self.user_memory.delete_for_member(
                    tenant_id=request.tenant_id, user_id=request.user_id
                ),
                CleanupStep.SESSIONS: lambda: self.sessions.delete_for_member(
                    tenant_id=request.tenant_id, user_id=request.user_id
                ),
                CleanupStep.EXECUTION_TEAMS: lambda: self.execution_teams.delete_for_member(
                    tenant_id=request.tenant_id, user_id=request.user_id
                ),
                CleanupStep.WORKSPACES: lambda: self.workspaces.delete_for_member(
                    tenant_id=request.tenant_id, user_id=request.user_id
                ),
            }

            for step in self._RESOURCES:
                if step in completed:
                    continue
                await self._transition(request, step, "started")
                try:
                    await operations[step]()
                except Exception as exc:
                    failed.append(step)
                    await self.ledger.mark_failed(request.operation_id, step, str(exc))
                    await self._transition(request, step, "failed", error=str(exc))
                    logger.warning(
                        "Member exit cleanup step failed operation=%s step=%s",
                        request.operation_id,
                        step.value,
                        exc_info=True,
                    )
                else:
                    await self.ledger.mark_completed(request.operation_id, step)
                    completed.add(step)
                    await self._transition(request, step, "completed")

            report = self._report(request, completed, failed)
            if not report.complete:
                raise MemberExitCleanupIncomplete(report)
            return report

    async def _transition(
        self,
        request: MemberExitRequest,
        step: CleanupStep,
        event: str,
        **details: Any,
    ) -> None:
        try:
            await self.audit.append(
                CleanupAuditEvent(
                    operation_id=request.operation_id,
                    step=step,
                    event=event,
                    tenant_id=request.tenant_id,
                    user_id=request.user_id,
                    actor_user_id=request.actor_user_id,
                    request_id=request.request_id,
                    occurred_at=self.clock(),
                    details=details,
                )
            )
        except Exception:
            # Audit failure must not make a successful deletion look pending;
            # the logger still leaves an operational breadcrumb for retry.
            logger.exception(
                "Member exit audit sink failed operation=%s step=%s event=%s",
                request.operation_id,
                step.value,
                event,
            )

    @staticmethod
    def _report(
        request: MemberExitRequest,
        completed: set[CleanupStep],
        failed: list[CleanupStep],
    ) -> MemberExitCleanupReport:
        return MemberExitCleanupReport(
            operation_id=request.operation_id,
            tenant_id=request.tenant_id,
            user_id=request.user_id,
            completed_steps=tuple(step for step in CleanupStep if step in completed),
            failed_steps=tuple(dict.fromkeys(failed)),
        )


class _RepositoryCleanup:
    """Small adapter helper that binds a repository to one resource step."""

    def __init__(self, callback: Callable[..., Awaitable[None]]) -> None:
        self._callback = callback

    async def delete_for_member(self, *, tenant_id: str, user_id: str) -> None:
        await self._callback(tenant_id=tenant_id, user_id=user_id)


def build_production_resource_adapters(
    adapters: ProductionMemberExitAdapters,
) -> tuple[
    PersonalConnectionCleanup,
    UserMemoryCleanup,
    SessionCleanup,
    ExecutionTeamCleanup,
    WorkspaceCleanup,
]:
    """Bind explicit PostgreSQL/Redis/Qdrant/workspace production seams."""
    return (
        _RepositoryCleanup(adapters.postgres.delete_personal_connections),
        _RepositoryCleanup(adapters.qdrant.delete_user_memory),
        _RepositoryCleanup(
            lambda **kwargs: _delete_session_backends(adapters, **kwargs)
        ),
        _RepositoryCleanup(adapters.redis.delete_execution_teams),
        _RepositoryCleanup(adapters.workspace.delete_workspaces),
    )


async def _delete_session_backends(
    adapters: ProductionMemberExitAdapters, *, tenant_id: str, user_id: str
) -> None:
    """Delete both durable SQL sessions and ephemeral Redis sessions."""
    await adapters.postgres.delete_sessions(tenant_id=tenant_id, user_id=user_id)
    await adapters.redis.delete_sessions(tenant_id=tenant_id, user_id=user_id)

{%- else %}
"""AgentScope member-exit cleanup is not configured."""
{%- endif %}
