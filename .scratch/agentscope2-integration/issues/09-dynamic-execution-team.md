# 09 — Dynamically form a single-level Execution Team

**What to build:** A leader can dynamically create and message workers from Tenant-enabled Agent Definitions, with a maximum of six workers and complete roster/status events in the existing product protocol.

**Blocked by:** 04 — Resume durable AgentScope sessions across processes; 08 — Enable curated Agent Definitions per Tenant.

**Status:** ready-for-human

- [ ] Only leaders create workers; workers cannot create nested teams or workers.
- [ ] Team state, inboxes, workspaces, and events are owned by the initiating User and Active Tenant.
- [ ] Redis MessageBus integration covers create, direct message, broadcast, worker completion, failure, and reconnect.
- [ ] Unit, backend integration, and Playwright team-flow tests pass 100%; changed code meets coverage gates.

## Verification

- Generated Execution Team contract tests: `6 passed`; Redis boundary test is marked integration and skipped without `AGENTSCOPE_INTEGRATION_REDIS_URL`.
- Coordinator enforces one Active Tenant, initiating-user ownership, leader-only worker creation, no nested teams, max six workers, enabled Definition selection, direct/broadcast inboxes, worker completion/failure isolation, and reconnect replay.
- AgentScope public MessageBus/TeamData/TeamRecord APIs are used; `agentscope[service]` supplies the public service scheduler dependency.
- Root generation assertion passed; Ruff, Ty focused check, and compile passed. Playwright/UI and real Redis tests remain environment-gated.
