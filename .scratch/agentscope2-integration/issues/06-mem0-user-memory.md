# 06 — Add tenant-scoped Mem0 User Memory

**What to build:** A User can recall and delete durable memory across conversations for one Tenant and Agent Definition; the User's Execution Team may use it, while other Tenant members cannot.

**Blocked by:** 03 — Add deterministic and GLM-5.2 runtime evaluation; 04 — Resume durable AgentScope sessions across processes.

**Status:** ready-for-human

- [ ] Mem0 is the only first-release memory backend and uses a Tenant/User/Agent Definition namespace.
- [ ] Memory read, write, delete, retention, and failure behavior are exposed through product-safe seams.
- [ ] Two-user/two-Tenant Qdrant integration tests prove no memory leakage; cross-session GLM recall meets the approved threshold.
- [ ] Unit and integration suites pass 100%; changed code meets coverage gates.

## Implementation notes

- Added `AgentScopeUserMemoryAdapter` with a Control Plane-issued
  `UserMemoryContext` and immutable Tenant/User/Agent Definition namespace.
- Mem0 is the only backend. Reads and writes require explicit consent; single
  deletion verifies namespace ownership through `get_all`; lifecycle
  `delete_all` remains available for member/tenant cleanup; retention dates
  are forwarded to Mem0.
- AgentScope integration uses the public `Mem0Middleware` constructor and
  `list_tools()` seam. No AgentScope source is modified.
- Generated-project contract tests cover isolation, fresh-context recall,
  consent, middleware wiring, deletion, retention, and product-safe backend
  failures. The Qdrant test is marked `integration` and skips without
  `AGENTSCOPE_INTEGRATION_QDRANT_URL`.

### Verification

- `pytest --noconftest tests/test_agentscope_memory.py -q`: **17 passed, 2 skipped**.
- `ruff check app/services/agentscope_memory.py tests/test_agentscope_memory.py`: **passed**.
- `ty check app/services/agentscope_memory.py tests/test_agentscope_memory.py`: **passed**.
- Real Qdrant/Mem0 and GLM recall remain environment-gated integration work.
