# 02 — Complete single-Agent AgentScope chat

**What to build:** A generated AgentScope project streams one Agent through the existing JWT WebSocket product flow with text, tool, HITL, cancellation, message persistence, usage, and Active Tenant authorization.

**Blocked by:** 01 — Generate a production-baseline AgentScope project.

**Status:** ready-for-agent

- [ ] Existing chat UI and channel entry points can execute AgentScope without exposing native AgentScope APIs.
- [ ] Tenant Viewer cannot start execution; cross-Tenant conversation access is rejected.
- [ ] Event adapter covers text, tool, HITL, cancellation, failure, and usage behavior.
- [ ] Unit and PostgreSQL-backed integration tests pass 100%; changed backend code meets coverage gates.
