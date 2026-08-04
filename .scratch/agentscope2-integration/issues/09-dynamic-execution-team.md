# 09 — Dynamically form a single-level Execution Team

**What to build:** A leader can dynamically create and message workers from Tenant-enabled Agent Definitions, with a maximum of six workers and complete roster/status events in the existing product protocol.

**Blocked by:** 04 — Resume durable AgentScope sessions across processes; 08 — Enable curated Agent Definitions per Tenant.

**Status:** ready-for-agent

- [ ] Only leaders create workers; workers cannot create nested teams or workers.
- [ ] Team state, inboxes, workspaces, and events are owned by the initiating User and Active Tenant.
- [ ] Redis MessageBus integration covers create, direct message, broadcast, worker completion, failure, and reconnect.
- [ ] Unit, backend integration, and Playwright team-flow tests pass 100%; changed code meets coverage gates.
