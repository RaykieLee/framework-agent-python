{%- if cookiecutter.use_agentscope %}
"""Control-plane adapter for AgentScope's public Mem0 middleware seam.

The generated application owns identity, consent, retention, and lifecycle.
Mem0 is only the durable backend.  A caller receives a scoped context from the
Control Plane and cannot provide raw Mem0 filters or collection names.
"""

from __future__ import annotations

import hashlib
import logging
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any, Literal, Protocol, cast

logger = logging.getLogger(__name__)


class UserMemoryError(RuntimeError):
    """Base class for product-safe User Memory failures."""


class MemoryConsentRequired(UserMemoryError):
    """Raised when the Control Plane has not granted memory consent."""


class MemoryBackendUnavailable(UserMemoryError):
    """Raised when Mem0 cannot complete an operation."""


class MemoryNotFound(UserMemoryError):
    """Raised when a memory is not inside the requested scope."""


class Mem0AsyncClient(Protocol):
    """The small async Mem0 boundary used by production and tests."""

    async def search(self, query: str, **kwargs: Any) -> Any: ...

    async def add(self, messages: list[dict[str, str]], **kwargs: Any) -> Any: ...

    async def get_all(self, **kwargs: Any) -> Any: ...

    async def delete(self, memory_id: str) -> Any: ...

    async def delete_all(self, **kwargs: Any) -> Any: ...


def _namespace_component(value: str) -> str:
    """Create a stable, delimiter-safe component for the Mem0 namespace."""
    raw = "".join(char if char.isalnum() or char in "._-" else "_" for char in value)
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]
    return f"{raw[:64] or 'empty'}-{digest}"


@dataclass(frozen=True, slots=True)
class UserMemoryScope:
    """Immutable identity for one User Memory namespace.

    The scope is issued by the Control Plane.  The adapter never accepts a
    caller-provided Mem0 filter, so Tenant, User, and Agent Definition remain
    bound together for every read/write/delete operation.
    """

    tenant_id: str
    user_id: str
    agent_definition_id: str

    def __post_init__(self) -> None:
        for field_name in ("tenant_id", "user_id", "agent_definition_id"):
            value = getattr(self, field_name)
            if not str(value).strip():
                raise ValueError(f"{field_name} is required for User Memory")

    @property
    def mem0_user_id(self) -> str:
        """Return the tenant-and-user component passed to Mem0."""
        return f"tenant:{_namespace_component(self.tenant_id)}:user:{_namespace_component(self.user_id)}"

    @property
    def mem0_agent_id(self) -> str:
        """Return the Agent Definition component passed to Mem0."""
        return f"agent-definition:{_namespace_component(self.agent_definition_id)}"

    @property
    def metadata(self) -> dict[str, str]:
        """Return defense-in-depth metadata for persisted records."""
        return {
            "tenant_id": self.tenant_id,
            "user_id": self.user_id,
            "agent_definition_id": self.agent_definition_id,
        }


@dataclass(frozen=True, slots=True)
class UserMemoryContext:
    """A Control Plane scope plus the consent decision for one execution."""

    scope: UserMemoryScope
    consent_granted: bool


@dataclass(frozen=True, slots=True)
class UserMemoryRecord:
    """Product-safe representation of a Mem0 result."""

    memory_id: str | None
    text: str
    score: float | None = None
    expires_at: datetime | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class UserMemoryWriteResult:
    """Stable result returned after a memory write."""

    memory_id: str | None
    text: str
    expires_at: datetime | None


class _ScopedMem0Client:
    """Bind AgentScope middleware's public client calls to one scope."""

    def __init__(self, client: Mem0AsyncClient, scope: UserMemoryScope) -> None:
        self._client = client
        self._scope = scope

    async def search(self, query: str, **kwargs: Any) -> Any:
        if kwargs.get("filters") != AgentScopeUserMemoryAdapter._filters(self._scope):
            raise MemoryConsentRequired("memory scope cannot be changed during execution")
        return await self._client.search(query, **kwargs)

    async def add(self, messages: list[dict[str, str]], **kwargs: Any) -> Any:
        expected = AgentScopeUserMemoryAdapter._filters(self._scope)
        if kwargs.get("user_id") != expected["user_id"] or kwargs.get("agent_id") != expected["agent_id"]:
            raise MemoryConsentRequired("memory scope cannot be changed during execution")
        metadata = dict(kwargs.pop("metadata", {}) or {})
        metadata.update(self._scope.metadata)
        kwargs["metadata"] = metadata
        return await self._client.add(messages, **kwargs)

    async def get_all(self, **kwargs: Any) -> Any:
        if kwargs.get("filters") != AgentScopeUserMemoryAdapter._filters(self._scope):
            raise MemoryConsentRequired("memory scope cannot be changed during execution")
        return await self._client.get_all(**kwargs)

    async def delete(self, memory_id: str) -> Any:
        return await self._client.delete(memory_id)

    async def delete_all(self, **kwargs: Any) -> Any:
        expected = AgentScopeUserMemoryAdapter._filters(self._scope)
        if kwargs.get("user_id") != expected["user_id"] or kwargs.get("agent_id") != expected["agent_id"]:
            raise MemoryConsentRequired("memory scope cannot be changed during execution")
        return await self._client.delete_all(**kwargs)


class AgentScopeUserMemoryAdapter:
    """Tenant-scoped Mem0 adapter with a public AgentScope middleware seam."""

    def __init__(
        self,
        client: Mem0AsyncClient,
        *,
        retention_days: int | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        if retention_days is not None and retention_days < 0:
            raise ValueError("retention_days must be non-negative")
        self.client = client
        self.retention_days = retention_days
        self.clock = clock or (lambda: datetime.now(UTC))

    async def search(
        self,
        context: UserMemoryContext,
        query: str,
        *,
        limit: int = 5,
        threshold: float | None = None,
    ) -> list[UserMemoryRecord]:
        """Retrieve durable memories for exactly one consented scope."""
        self._require_consent(context)
        if not query.strip():
            return []
        if limit < 1:
            raise ValueError("limit must be positive")
        kwargs: dict[str, Any] = {
            "filters": self._filters(context.scope),
            "top_k": limit,
        }
        if threshold is not None:
            kwargs["threshold"] = threshold
        raw = await self._call("search", query, **kwargs)
        return self._parse_records(raw, context.scope, include_scores=True)

    async def read(
        self,
        context: UserMemoryContext,
        query: str,
        *,
        limit: int = 5,
        threshold: float | None = None,
    ) -> list[UserMemoryRecord]:
        """Alias using the Control Plane's read terminology."""
        return await self.search(context, query, limit=limit, threshold=threshold)

    async def remember(
        self,
        context: UserMemoryContext,
        text: str,
        *,
        expiration_date: datetime | None = None,
        infer: bool = True,
    ) -> UserMemoryWriteResult:
        """Persist one fact using Mem0's user/agent namespace."""
        self._require_consent(context)
        if not text.strip():
            raise ValueError("memory text is required")
        expires_at = self._resolve_expiration(expiration_date)
        kwargs: dict[str, Any] = {
            "user_id": context.scope.mem0_user_id,
            "agent_id": context.scope.mem0_agent_id,
            "metadata": context.scope.metadata,
        }
        if expires_at is not None:
            kwargs["expiration_date"] = expires_at
        if not infer:
            kwargs["infer"] = False
        raw = await self._call("add", [{"role": "user", "content": text}], **kwargs)
        records = self._parse_records(raw, context.scope)
        first = records[0] if records else None
        return UserMemoryWriteResult(
            memory_id=first.memory_id if first else None,
            text=text,
            expires_at=expires_at,
        )

    async def write(
        self,
        context: UserMemoryContext,
        text: str,
        *,
        expiration_date: datetime | None = None,
        infer: bool = True,
    ) -> UserMemoryWriteResult:
        """Alias using the Control Plane's write terminology."""
        return await self.remember(
            context,
            text,
            expiration_date=expiration_date,
            infer=infer,
        )

    async def delete(self, context: UserMemoryContext, memory_id: str) -> None:
        """Delete one memory only after proving it belongs to this scope."""
        if not memory_id.strip():
            raise ValueError("memory_id is required")
        rows = await self._call(
            "get_all",
            filters=self._filters(context.scope),
            show_expired=True,
        )
        records = self._parse_records(rows, context.scope)
        if not any(record.memory_id == memory_id for record in records):
            raise MemoryNotFound("memory does not belong to the requested scope")
        await self._call("delete", memory_id)

    async def delete_all(self, scope: UserMemoryScope) -> None:
        """Delete all private memory for a scope during lifecycle cleanup."""
        await self._call(
            "delete_all",
            user_id=scope.mem0_user_id,
            agent_id=scope.mem0_agent_id,
        )

    def build_middleware(
        self,
        context: UserMemoryContext,
        *,
        mode: Literal["static_control", "agent_control", "both"] = "both",
        top_k: int = 5,
        threshold: float | None = None,
    ) -> Any:
        """Build AgentScope's public ``Mem0Middleware`` for this context.

        The returned middleware is intentionally created per execution.  It
        captures one immutable namespace and cannot be reused for another
        Active Tenant.
        """
        self._require_consent(context)
        from agentscope.middleware import Mem0Middleware

        return Mem0Middleware(
            user_id=context.scope.mem0_user_id,
            agent_id=context.scope.mem0_agent_id,
            client=cast(Any, _ScopedMem0Client(self.client, context.scope)),
            mode=mode,
            top_k=top_k,
            threshold=threshold,
            scope_search_by_agent=True,
        )

    @staticmethod
    def _filters(scope: UserMemoryScope) -> dict[str, str]:
        return {
            "user_id": scope.mem0_user_id,
            "agent_id": scope.mem0_agent_id,
        }

    def _resolve_expiration(self, expiration_date: datetime | None) -> datetime | None:
        now = self.clock()
        if now.tzinfo is None:
            now = now.replace(tzinfo=UTC)
        if expiration_date is None and self.retention_days is not None:
            expiration_date = now + timedelta(days=self.retention_days)
        if expiration_date is not None:
            if expiration_date.tzinfo is None:
                expiration_date = expiration_date.replace(tzinfo=UTC)
            if expiration_date <= now:
                raise ValueError("expiration_date must be in the future")
        return expiration_date

    async def _call(self, method: str, *args: Any, **kwargs: Any) -> Any:
        try:
            operation = getattr(self.client, method)
            return await operation(*args, **kwargs)
        except UserMemoryError:
            raise
        except Exception as exc:  # noqa: BLE001
            logger.warning("AgentScope memory %s failed", method)
            raise MemoryBackendUnavailable("memory backend unavailable") from exc

    @classmethod
    def _parse_records(
        cls,
        raw: Any,
        scope: UserMemoryScope,
        *,
        include_scores: bool = False,
    ) -> list[UserMemoryRecord]:
        raw_items = raw.get("results", raw.get("memories", [])) if isinstance(raw, Mapping) else raw
        if not isinstance(raw_items, Sequence) or isinstance(raw_items, (str, bytes)):
            return []
        records: list[UserMemoryRecord] = []
        for item in raw_items:
            if isinstance(item, str):
                # A bare text result carries no proof of its tenant/user/
                # agent namespace.  Reject it rather than risk a leak from a
                # misconfigured or legacy Mem0 collection.
                continue
            if not isinstance(item, Mapping):
                continue
            metadata = item.get("metadata")
            metadata_map = dict(metadata) if isinstance(metadata, Mapping) else {}
            if not cls._metadata_matches_scope(metadata_map, scope):
                continue
            text = item.get("memory") or item.get("text") or item.get("content")
            if not isinstance(text, str) or not text.strip():
                continue
            score = item.get("score") if include_scores else None
            records.append(
                UserMemoryRecord(
                    memory_id=str(item["id"]) if item.get("id") is not None else None,
                    text=text,
                    score=float(score) if isinstance(score, (int, float)) else None,
                    expires_at=cls._parse_datetime(item.get("expiration_date")),
                    metadata=metadata_map,
                )
            )
        return records

    @staticmethod
    def _metadata_matches_scope(metadata: Mapping[str, Any], scope: UserMemoryScope) -> bool:
        expected = scope.metadata
        return all(key in metadata and str(metadata[key]) == value for key, value in expected.items())

    @staticmethod
    def _parse_datetime(value: Any) -> datetime | None:
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                return None
        return None

    @staticmethod
    def _require_consent(context: UserMemoryContext) -> None:
        if not context.consent_granted:
            raise MemoryConsentRequired("memory consent is required")
{%- else %}
"""AgentScope User Memory is not selected."""
{%- endif %}
