# 13 — Complete Tenant Purge across all stores

**What to build:** Deleting a Tenant starts an auditable asynchronous purge of business records, AgentScope state, Redis keys, Qdrant memory/KB data, workspaces, connections, and derived caches.

**Blocked by:** 05 — Retrieve Control Plane Knowledge Bases through AgentScope; 12 — Clean private execution state when members leave.

**Status:** ready-for-agent

- [ ] Purge is tenant-scoped, retryable, observable, and cannot touch another Tenant.
- [ ] Successful purge leaves no discoverable SQL, Redis, vector, workspace, memory, or credential residue.
- [ ] Failure reports identify incomplete stores without claiming false completion.
- [ ] Unit, full-stack Docker integration, and cross-Tenant negative tests pass 100%; changed code meets coverage gates.
