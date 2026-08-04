# 12 — Clean private execution state when members leave

**What to build:** Leaving a Tenant immediately revokes access and removes the member's Personal Connections, User Memory, sessions, Execution Teams, and workspace state while preserving Tenant Conversations for organizational continuity.

**Blocked by:** 06 — Add tenant-scoped Mem0 User Memory; 07 — Create single-Tenant Personal Connections; 09 — Dynamically form a single-level Execution Team; 11 — Aggregate Team Run billing and stop propagation.

**Status:** ready-for-human

- [ ] Cleanup is idempotent, auditable, and safe to retry after partial failure.
- [ ] Former members cannot read, subscribe, execute, or mutate retained Tenant Conversations.
- [ ] Integration tests verify cleanup in PostgreSQL, Redis, Qdrant, and workspace storage.
- [ ] Unit/integration tests pass 100%; changed code meets coverage gates.

## Implementation notes

- Added `MemberExitCleanupService` as a Control-Plane lifecycle boundary. It
  revokes membership first, then deletes Personal Connections, User Memory,
  sessions, Execution Team private state, and workspaces. Tenant Conversations
  and messages are intentionally not a cleanup target.
- Each step is protected by a durable idempotency-ledger seam and append-only
  audit events. Partial failures are reported after attempting independent
  steps; retries skip completed steps and replay only failed steps.
- `TenantConversationAccess` provides an explicit read/subscribe/execute/mutate
  denial seam for revoked members. PostgreSQL, Redis, Qdrant/Mem0, and workspace
  repository protocols are named in `ProductionMemberExitAdapters`.
- `MemberService.remove` and `MemberService.leave` accept an optional cleanup
  service and invoke it after membership deletion, preserving existing RBAC
  checks while ensuring the private-state workflow is part of the exit path.

### Verification

- Generated AgentScope + Teams project member-exit contract suite: **4 passed**.
- Generated existing member service suite: **30 passed**.
- Generated focused Ruff: **passed**; focused Ty: **passed**; compileall: **passed**.
- Non-AgentScope generation removes the new service and test files.
- Generated matrix Ruff passed; Ty exited 0 with 17 pre-existing template
  warnings. The matrix test runner requires `uv`/`uvx` on PATH; local manual
  rerun with those binaries passed.
- Live PostgreSQL/Redis/Qdrant/workspace execution remains environment-gated;
  the production adapter test verifies all four boundaries with fakes.
