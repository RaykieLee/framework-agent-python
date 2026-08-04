# 04 — Resume durable AgentScope sessions across processes

**What to build:** A conversation reconnects to its mapped AgentScope session after process restart or WebSocket reconnect, replaying buffered events exactly once under Redis locks and tenant-prefixed keys.

**Blocked by:** 02 — Complete single-Agent AgentScope chat.

**Status:** ready-for-human

- [ ] Conversation/session mapping, request IDs, event replay, locks, and cancellation are durable.
- [ ] Duplicate requests do not double-charge or duplicate assistant messages.
- [ ] Multi-process PostgreSQL + Redis integration tests cover restart, reconnect, replay, lock contention, and cross-Tenant subscription denial.
- [ ] Unit and integration suites pass 100%; changed backend code meets coverage gates.

## Verification

- Durable-session generated tests: `6 passed`, including reconnect mapping, tenant-prefixed keys, duplicate request/charge idempotency, lock contention, replay-once, cancellation, and AgentSession runner-once integration.
- Generated AgentScope template regression: `4 passed`; Ruff and Ty checks for the durable seam passed.
- PostgreSQL/Redis multi-process execution was not started because the local Docker daemon stalled while pulling images; production adapters are protocol-bound and the in-process fake covers behavior without services.
