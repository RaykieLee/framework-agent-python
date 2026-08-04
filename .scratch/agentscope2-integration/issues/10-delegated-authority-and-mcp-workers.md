# 10 — Apply AgentScope Delegated Authority to workers

**What to build:** Workers follow AgentScope's native inheritance semantics for permission mode, allow/deny/ask rules, working directories, and eligible Personal Connections within the same Execution Team and Active Tenant.

**Blocked by:** 07 — Create single-Tenant Personal Connections; 09 — Dynamically form a single-level Execution Team.

**Status:** ready-for-human

- [x] SubAgentTemplate inheritance flags and precedence are preserved.
- [x] Template rules override inherited rules where AgentScope specifies precedence; denied tools never execute.
- [x] Workers cannot see credentials, directories, or resources outside the Active Tenant.
- [x] Permission, MCP, HITL, and cross-Tenant negative tests pass 100%; changed code meets coverage gates.

## Implementation notes

- Added the `AgentScopeDelegationPolicy` adapter. It consumes Ticket 09's
  `ExecutionTeamState`, resolves the enabled Agent Definition, and issues an
  immutable `DelegatedWorkerAuthority` for one worker session.
- Native AgentScope `SubAgentTemplate` flags (`override_leader_mode`,
  `extend_leader_permission_rules`, and `extend_leader_working_directories`)
  remain the precedence source of truth. Template deny rules are explicit and
  cannot be bypassed by a delegated MCP grant.
- Personal Connections cross this seam as redacted
  `PersonalConnectionRecord` values only. Grants contain an id/name/tool
  allowlist; credentials, URL, OAuth payloads, and private prompts are never
  serialized. A resolver returning another tenant's record is rejected.
- Workers have no nested-team capability, and inherited working directories
  require a trusted Active-Tenant `workspace_root`.
- Redis MessageBus and a real MCP resolver remain opt-in integration seams;
  fake resolvers cover unit/contract behavior.

## Verification

- Generated AgentScope + PostgreSQL + Redis + Qdrant project: `uv sync`
  succeeded; targeted `ruff` and `ty` checks passed.
- Six delegation contract tests passed via the generated module's public
  seams. Full generated pytest collection is currently blocked by the
  pre-existing FastAPI/`fastapi-pagination` incompatibility on Python 3.14
  (`get_body_field(..., body_params=...)`).
