# 05 — Retrieve Control Plane Knowledge Bases through AgentScope

**What to build:** A user-selected Knowledge Base remains owned and ingested by the Control Plane while AgentScope retrieves authorized content with citations and mandatory Tenant/KB filtering.

**Blocked by:** 04 — Resume durable AgentScope sessions across processes.

**Status:** ready-for-agent

- [ ] No second AgentScope KB CRUD or ingestion path is introduced.
- [ ] Personal, organization, and Platform Resource scopes resolve only within the Active Tenant rules.
- [ ] Real vector-store tests prove zero cross-Tenant or cross-KB leakage, including forged IDs and filters.
- [ ] Unit, integration, and grounded GLM evaluation pass 100% for security assertions; changed code meets coverage gates.
