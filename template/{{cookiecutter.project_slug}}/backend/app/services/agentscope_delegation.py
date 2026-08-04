{%- if cookiecutter.use_agentscope and cookiecutter.enable_teams and cookiecutter.use_jwt %}
"""Non-escalating AgentScope worker authority.

The Control Plane resolves one immutable authority object for each worker.
AgentScope still performs the native permission merge when it creates the
worker from :class:`~agentscope.app.SubAgentTemplate`; this adapter only
supplies the template and the tenant-bound MCP grants.  Credentials, URLs,
and private prompts never cross this seam.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import PurePosixPath
from typing import Any, Protocol
from uuid import UUID

from agentscope.app import SubAgentTemplate
from agentscope.permission import (
    AdditionalWorkingDirectory,
    PermissionContext,
    PermissionMode,
    PermissionRule,
)

from app.core.exceptions import AuthorizationError, NotFoundError, ValidationError
from app.schemas.agentscope_agent_definition import AgentDefinitionRuntime
from app.services.agentscope_execution_team import ExecutionTeamContext, ExecutionTeamState


class DelegationError(RuntimeError):
    """Base error raised when delegated authority cannot be issued."""


class WorkerAuthorityDenied(DelegationError):
    """The worker is not allowed to perform the requested operation."""


class CrossTenantConnection(DelegationError):
    """A Personal Connection is outside the Active Tenant boundary."""


class NestedDelegationDenied(WorkerAuthorityDenied):
    """Workers cannot create workers or nested Execution Teams."""


class PersonalConnectionResolver(Protocol):
    """Control-Plane seam for enabled, tenant-bound Personal Connections."""

    async def list_for_execution(
        self,
        *,
        tenant_id: str,
        user_id: str,
    ) -> Sequence["PersonalConnectionRecord"]: ...


@dataclass(frozen=True, slots=True)
class PersonalConnectionRecord:
    """Redacted Control-Plane connection projection.

    A resolver must never put URL, headers, bearer tokens, or OAuth payloads
    in this DTO.  The runtime may later turn the id into a short-lived client
    through another server-side adapter.
    """

    connection_id: str
    tenant_id: str
    user_id: str
    name: str
    allowed_tools: tuple[str, ...] | None = None

    def __post_init__(self) -> None:
        for field_name in ("connection_id", "tenant_id", "user_id", "name"):
            if not str(getattr(self, field_name)).strip():
                raise ValidationError(message=f"{field_name} is required")
        if self.allowed_tools is not None and any(not str(tool).strip() for tool in self.allowed_tools):
            raise ValidationError(message="MCP tool names must not be empty")


@dataclass(frozen=True, slots=True)
class DelegatedMCPGrant:
    """A least-privilege MCP grant without connection credentials."""

    connection_id: str
    name: str
    allowed_tools: tuple[str, ...]

    def allows(self, tool_name: str) -> bool:
        return tool_name in self.allowed_tools

    def to_payload(self) -> dict[str, Any]:
        # Deliberately no URL, headers, OAuth payload, or bearer token.
        return {
            "connection_id": self.connection_id,
            "name": self.name,
            "allowed_tools": list(self.allowed_tools),
        }


@dataclass(frozen=True, slots=True)
class DelegatedWorkerAuthority:
    """Immutable authority passed to one AgentScope worker.

    ``to_payload`` is safe for audit events: it excludes all private prompt
    and credential material.  The native ``SubAgentTemplate`` remains the
    source of truth for inheritance and precedence semantics.
    """

    context: ExecutionTeamContext
    team_id: str
    worker_session_id: str
    definition_slug: str
    definition_version: int
    template: SubAgentTemplate
    mcp_grants: tuple[DelegatedMCPGrant, ...] = ()
    denied_tools: frozenset[str] = frozenset()
    worker_can_create_team: bool = False

    def __post_init__(self) -> None:
        if self.context.tenant_id == "" or self.context.user_id == "":
            raise WorkerAuthorityDenied("worker authority requires an Active Tenant")
        if self.worker_can_create_team:
            raise NestedDelegationDenied("workers cannot create nested teams")

    @property
    def allowed_mcp_tools(self) -> frozenset[str]:
        return frozenset(tool for grant in self.mcp_grants for tool in grant.allowed_tools)

    def check_tool(self, tool_name: str, *, connection_name: str | None = None) -> None:
        """Reject every denied or non-granted MCP operation before execution."""
        if tool_name in self.denied_tools:
            raise WorkerAuthorityDenied(f"tool denied by the worker policy: {tool_name}")
        if connection_name is not None:
            grant = next((item for item in self.mcp_grants if item.name == connection_name), None)
            if grant is None or not grant.allows(tool_name):
                raise WorkerAuthorityDenied(f"MCP tool is not delegated: {connection_name}/{tool_name}")

    def assert_can_create_team(self) -> None:
        raise NestedDelegationDenied("workers cannot create workers or nested Execution Teams")

    def to_payload(self) -> dict[str, Any]:
        """Return a redacted audit projection, never a native template dump."""
        return {
            "tenant_id": self.context.tenant_id,
            "user_id": self.context.user_id,
            "conversation_id": self.context.conversation_id,
            "team_id": self.team_id,
            "worker_session_id": self.worker_session_id,
            "definition_slug": self.definition_slug,
            "definition_version": self.definition_version,
            "mcp_grants": [grant.to_payload() for grant in self.mcp_grants],
            "denied_tools": sorted(self.denied_tools),
            "worker_can_create_team": False,
        }


class AgentScopeDelegationPolicy:
    """Resolve worker authority from Ticket 09 team state and Control Plane data."""

    def __init__(self, definition_resolver: Any, connection_resolver: PersonalConnectionResolver) -> None:
        self.definition_resolver = definition_resolver
        self.connection_resolver = connection_resolver

    async def issue(
        self,
        context: ExecutionTeamContext,
        team: ExecutionTeamState,
        *,
        worker_session_id: str,
        leader_permission_context: PermissionContext | None = None,
    ) -> DelegatedWorkerAuthority:
        """Issue one authority after proving the team and Active Tenant match."""
        if team.context != context:
            raise AuthorizationError(message="Execution Team is outside the Active Tenant")
        worker = next(
            (item for item in team.workers.values() if item.session_id == worker_session_id),
            None,
        )
        if worker is None:
            raise NotFoundError(message="Execution Team worker not found")
        definitions = await self.definition_resolver.list_enabled(
            tenant_id=context.tenant_id,
            user_id=context.user_id,
        )
        definition = next(
            (
                item
                for item in definitions
                if item.slug == worker.definition_slug and item.version == worker.definition_version
            ),
            None,
        )
        if definition is None:
            raise WorkerAuthorityDenied("worker Agent Definition is no longer enabled")
        connections = await self.connection_resolver.list_for_execution(
            tenant_id=context.tenant_id,
            user_id=context.user_id,
        )
        policy = _policy(definition.tool_policy)
        grants = _mcp_grants(
            connections,
            policy,
            tenant_id=context.tenant_id,
            user_id=context.user_id,
        )
        template = _build_template(definition, policy, leader_permission_context)
        return DelegatedWorkerAuthority(
            context=context,
            team_id=team.team_id,
            worker_session_id=worker_session_id,
            definition_slug=definition.slug,
            definition_version=definition.version,
            template=template,
            mcp_grants=grants,
            denied_tools=frozenset(policy["deny_tools"]),
        )


def _policy(raw: Mapping[str, Any] | None) -> dict[str, Any]:
    """Normalize the published definition policy without accepting escalation."""
    value = dict(raw or {})
    known = {
        "permission_mode",
        "override_leader_mode",
        "extend_leader_permission_rules",
        "extend_leader_working_directories",
        "workspace_root",
        "working_directories",
        "allow_tools",
        "deny_tools",
        "ask_tools",
        "mcp_connections",
        "mcp_tools",
    }
    unknown = set(value) - known
    if unknown:
        raise ValidationError(message="Unknown worker delegation policy", details={"keys": sorted(unknown)})
    raw_mode = value.get("permission_mode", "default")
    mode = raw_mode.value if isinstance(raw_mode, PermissionMode) else str(raw_mode).lower()
    try:
        PermissionMode(mode)
    except ValueError as exc:
        raise ValidationError(message="Invalid AgentScope permission mode") from exc
    normalized: dict[str, Any] = {
        "permission_mode": mode,
        "override_leader_mode": bool(value.get("override_leader_mode", False)),
        "extend_leader_permission_rules": bool(value.get("extend_leader_permission_rules", True)),
        "extend_leader_working_directories": bool(value.get("extend_leader_working_directories", True)),
        "workspace_root": str(value.get("workspace_root", "")).strip(),
        "working_directories": tuple(_as_values(value.get("working_directories"))),
        "allow_tools": frozenset(_as_values(value.get("allow_tools"))),
        "deny_tools": frozenset(_as_values(value.get("deny_tools"))),
        "ask_tools": frozenset(_as_values(value.get("ask_tools"))),
        "mcp_connections": frozenset(_as_values(value.get("mcp_connections"))),
        "mcp_tools": {
            str(name): frozenset(_as_values(tools))
            for name, tools in dict(value.get("mcp_tools") or {}).items()
        },
    }
    if normalized["override_leader_mode"] and mode == PermissionMode.BYPASS.value:
        raise WorkerAuthorityDenied(
            "a worker cannot override the leader with AgentScope BYPASS mode"
        )
    if normalized["deny_tools"] & normalized["allow_tools"]:
        # Deny is authoritative; keeping the overlap explicit makes the
        # native PermissionEngine's first-match precedence unambiguous.
        normalized["allow_tools"] = normalized["allow_tools"] - normalized["deny_tools"]
    return normalized


def _build_template(
    definition: AgentDefinitionRuntime,
    policy: Mapping[str, Any],
    leader_context: PermissionContext | None,
) -> SubAgentTemplate:
    """Build a native template while preserving AgentScope's merge flags."""
    permission = PermissionContext(mode=PermissionMode(policy["permission_mode"]))
    for path in policy["working_directories"]:
        if not _safe_working_directory(path):
            raise WorkerAuthorityDenied("worker working directory must be absolute and normalized")
        if policy["workspace_root"] and not _is_within(path, policy["workspace_root"]):
            raise WorkerAuthorityDenied(
                "worker working directory is outside the Active Tenant workspace"
            )
        permission.working_directories[path] = AdditionalWorkingDirectory(
            path=path,
            source="agentDefinition",
        )
    if leader_context is not None and policy["extend_leader_working_directories"]:
        root = policy["workspace_root"]
        if not root or not _safe_working_directory(root):
            if leader_context.working_directories:
                raise WorkerAuthorityDenied(
                    "leader working directories require a tenant workspace root"
                )
        else:
            for leader_path in leader_context.working_directories:
                if not _is_within(leader_path, root):
                    raise WorkerAuthorityDenied(
                        "leader working directory is outside the Active Tenant workspace"
                    )
    _add_rules(permission.allow_rules, policy["allow_tools"], "allow", "agentDefinition")
    _add_rules(permission.deny_rules, policy["deny_tools"], "deny", "agentDefinition")
    _add_rules(permission.ask_rules, policy["ask_tools"], "ask", "agentDefinition")
    # The worker receives its own private prompt through the native template;
    # the audit authority deliberately redacts it.  No leader prompt is copied.
    prompt = (
        "You are {member_name}, the {member_description} worker in team "
        "'{team_name}' led by {leader_name}.\n\n"
        "Team purpose: {team_description}\n"
        "Complete only the delegated task and report through TeamSay."
    )
    return SubAgentTemplate(
        type=definition.slug,
        description=definition.role,
        system_prompt_template=prompt,
        permission_context=permission,
        override_leader_mode=policy["override_leader_mode"],
        extend_leader_permission_rules=policy["extend_leader_permission_rules"],
        extend_leader_working_directories=policy["extend_leader_working_directories"],
    )


def _mcp_grants(
    connections: Sequence[PersonalConnectionRecord],
    policy: Mapping[str, Any],
    *,
    tenant_id: str,
    user_id: str,
) -> tuple[DelegatedMCPGrant, ...]:
    grants: list[DelegatedMCPGrant] = []
    for connection in connections:
        if connection.tenant_id != tenant_id or connection.user_id != user_id:
            raise CrossTenantConnection("a Personal Connection crossed the Active Tenant boundary")
        if connection.name not in policy["mcp_connections"]:
            continue
        requested = policy["mcp_tools"].get(connection.name)
        source = set(connection.allowed_tools or ())
        allowed = requested if requested is not None else source
        if requested is not None and source:
            allowed = requested & source
        allowed -= set(policy["deny_tools"])
        if policy["allow_tools"]:
            allowed &= set(policy["allow_tools"])
        if allowed:
            grants.append(
                DelegatedMCPGrant(
                    connection_id=connection.connection_id,
                    name=connection.name,
                    allowed_tools=tuple(sorted(allowed)),
                )
            )
    return tuple(grants)


def _add_rules(target: dict[str, list[PermissionRule]], tools: Sequence[str], behavior: str, source: str) -> None:
    for tool_name in tools:
        target.setdefault(tool_name, []).append(
            PermissionRule(tool_name=tool_name, rule_content=None, behavior=behavior, source=source)
        )


def _as_values(value: Any) -> tuple[str, ...]:
    """Normalize optional policy list fields without iterating ``None``/chars."""
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,)
    try:
        return tuple(str(item) for item in value)
    except TypeError as exc:
        raise ValidationError(message="Worker delegation policy lists must be iterable") from exc


def _safe_working_directory(path: str) -> bool:
    parsed = PurePosixPath(path)
    return parsed.is_absolute() and ".." not in parsed.parts


def _is_within(path: str, root: str) -> bool:
    """Check a normalized POSIX path without following symlinks."""
    if not _safe_working_directory(path) or not _safe_working_directory(root):
        return False
    path_parts = PurePosixPath(path).parts
    root_parts = PurePosixPath(root).parts
    return path_parts[: len(root_parts)] == root_parts


__all__ = [
    "AgentScopeDelegationPolicy",
    "CrossTenantConnection",
    "DelegatedMCPGrant",
    "DelegatedWorkerAuthority",
    "DelegationError",
    "NestedDelegationDenied",
    "PersonalConnectionRecord",
    "PersonalConnectionResolver",
    "WorkerAuthorityDenied",
]
{%- else %}
"""AgentScope worker delegation is not configured."""
{%- endif %}
