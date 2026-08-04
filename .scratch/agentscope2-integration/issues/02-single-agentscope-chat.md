# 02 — Complete single-Agent AgentScope chat

**What to build:** A generated AgentScope project streams one Agent through the existing JWT WebSocket product flow with text, tool, HITL, cancellation, message persistence, usage, and Active Tenant authorization.

**Blocked by:** 01 — Generate a production-baseline AgentScope project.

**Status:** ready-for-human

- [ ] Existing chat UI and channel entry points can execute AgentScope without exposing native AgentScope APIs.
- [ ] Tenant Viewer cannot start execution; cross-Tenant conversation access is rejected.
- [ ] Event adapter covers text, tool, HITL, cancellation, failure, and usage behavior.
- [ ] Unit and PostgreSQL-backed integration tests pass 100%; changed backend code meets coverage gates.

## Verification

- Generated AgentScope seam tests: `5 passed` with `--noconftest` (in-process, no network).
- Generated project dependency sync, Ruff, and compileall passed.
- Root AgentScope generation regression tests: `4 passed`; config tests: `3 passed`.
- The normal generated pytest suite remains blocked by the pre-existing FastAPI/fastapi-pagination incompatibility recorded in Ticket 01; this ticket adds no database schema changes.
