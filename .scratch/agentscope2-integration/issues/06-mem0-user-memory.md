# 06 — Add tenant-scoped Mem0 User Memory

**What to build:** A User can recall and delete durable memory across conversations for one Tenant and Agent Definition; the User's Execution Team may use it, while other Tenant members cannot.

**Blocked by:** 03 — Add deterministic and GLM-5.2 runtime evaluation; 04 — Resume durable AgentScope sessions across processes.

**Status:** ready-for-agent

- [ ] Mem0 is the only first-release memory backend and uses a Tenant/User/Agent Definition namespace.
- [ ] Memory read, write, delete, retention, and failure behavior are exposed through product-safe seams.
- [ ] Two-user/two-Tenant Qdrant integration tests prove no memory leakage; cross-session GLM recall meets the approved threshold.
- [ ] Unit and integration suites pass 100%; changed code meets coverage gates.
