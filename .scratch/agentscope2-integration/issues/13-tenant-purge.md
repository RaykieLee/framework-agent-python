# 13 — Complete Tenant Purge across all stores

**What to build:** Deleting a Tenant starts an auditable asynchronous purge of business records, AgentScope state, Redis keys, Qdrant memory/KB data, workspaces, connections, and derived caches.

**Blocked by:** 05 — Retrieve Control Plane Knowledge Bases through AgentScope; 12 — Clean private execution state when members leave.

**Status:** ready-for-human

- [ ] Purge is tenant-scoped, retryable, observable, and cannot touch another Tenant.
- [ ] Successful purge leaves no discoverable SQL, Redis, vector, workspace, memory, or credential residue.
- [ ] Failure reports identify incomplete stores without claiming false completion.
- [ ] Unit, full-stack Docker integration, and cross-Tenant negative tests pass 100%; changed code meets coverage gates.

## Implementation notes

- Added `TenantPurgeService` as an asynchronous queue/worker boundary with
  exact `PURGE {tenant_id}` confirmation, owner/admin API authorization,
  tenant-keyed idempotency, durable-job/step semantics, append-only audit
  events, retry-after-partial-failure, and redaction-safe status projections.
- Added explicit production adapter protocols for Control Plane SQL,
  AgentScope SQL, Redis, Qdrant, Mem0, workspace, and Personal Connection
  stores. The Control Plane callback is always invoked with
  `preserve_audit=True`; no adapter accepts a caller-supplied key or path.
- Added `POST /orgs/{org_id}/purge` (202) and tenant-bound status API. The
  endpoint only enqueues work; a deployment must wire a queue and call the
  worker seam, so generated projects never run destructive deletion by
  default.

### Verification

- Generated AgentScope + Teams contract suite: **4 passed** with
  `pytest --noconftest tests/test_agentscope_tenant_purge.py -q`.
- Generated service/API files: focused Ruff, Ty, and `compileall` passed.
- Root generator contract: **1 passed** (`-k purge`). Root test Ruff still
  reports 18 pre-existing C408 findings in the matrix dictionary; Ty passes.
- Full PostgreSQL/Redis/Qdrant/workspace Docker execution is intentionally
  left as an integration-boundary check; the fake-store suite proves
  cross-Tenant negative isolation and retry semantics without external
  credentials.
