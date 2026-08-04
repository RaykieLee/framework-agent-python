# 11 — Aggregate Team Run billing and stop propagation

**What to build:** Leader and worker model/tool/retrieval/memory usage aggregates into one Team Run; worker failures are isolated, while user stop, budget exhaustion, quota, or security termination cancels the entire team.

**Blocked by:** 09 — Dynamically form a single-level Execution Team.

**Status:** ready-for-human

- [x] Usage attribution is tied to initiating User, Active Tenant, and conversation with per-worker diagnostics.
- [x] Run and Tenant budgets stop all workers without losing already completed partial results.
- [x] A failed worker reports to leader without silently escaping billing or cancellation rules.
- [x] State-machine/unit and PostgreSQL + Redis integration tests pass 100%; changed code meets coverage gates.

## Implementation notes

- Added the `AgentScopeTeamRunService` adapter around Ticket 09's flat roster.
  `TeamRunContext` binds every run to the initiating User, Active Tenant,
  conversation, and team; `MemberUsage` keeps per-worker model/tool/retrieval/
  memory diagnostics while all credits remain one billable run.
- Run and Tenant credit limits transition the state machine through
  `stopping` to `stopped`, canceling every still-running member and preserving
  completed results. User and security stops share the same propagation path.
- Worker failures emit a leader-visible event and do not cancel siblings. Usage
  event IDs and terminal-state guards make charging and finalization idempotent.
- `RedisPostgresTeamRunStore` defines the production PostgreSQL source-of-truth
  and Redis-lock seam. `RedisTeamRunCancellation` adds tenant-prefixed
  cancellation flags for workers in other processes; no AgentScope source is
  modified.

## Verification

- Generated AgentScope + PostgreSQL + Redis + Qdrant + Billing + Credits
  project: targeted Ruff and Ty checks pass.
- Team Run contract suite: `12 passed`; the marked PostgreSQL/Redis boundary is
  skipped unless the generated app injects live infrastructure fixtures.
- Root generation assertion: `1 passed`.
- Normal generated pytest collection remains environment-blocked by the
  pre-existing FastAPI/`fastapi-pagination` `get_body_field(body_params=...)`
  incompatibility; no Ticket 11 test failure is hidden by that boundary.
