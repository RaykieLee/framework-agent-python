# 12 — Clean private execution state when members leave

**What to build:** Leaving a Tenant immediately revokes access and removes the member's Personal Connections, User Memory, sessions, Execution Teams, and workspace state while preserving Tenant Conversations for organizational continuity.

**Blocked by:** 06 — Add tenant-scoped Mem0 User Memory; 07 — Create single-Tenant Personal Connections; 09 — Dynamically form a single-level Execution Team; 11 — Aggregate Team Run billing and stop propagation.

**Status:** ready-for-agent

- [ ] Cleanup is idempotent, auditable, and safe to retry after partial failure.
- [ ] Former members cannot read, subscribe, execute, or mutate retained Tenant Conversations.
- [ ] Integration tests verify cleanup in PostgreSQL, Redis, Qdrant, and workspace storage.
- [ ] Unit/integration tests pass 100%; changed code meets coverage gates.
