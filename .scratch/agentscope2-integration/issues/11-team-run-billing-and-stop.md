# 11 — Aggregate Team Run billing and stop propagation

**What to build:** Leader and worker model/tool/retrieval/memory usage aggregates into one Team Run; worker failures are isolated, while user stop, budget exhaustion, quota, or security termination cancels the entire team.

**Blocked by:** 09 — Dynamically form a single-level Execution Team.

**Status:** ready-for-agent

- [ ] Usage attribution is tied to initiating User, Active Tenant, and conversation with per-worker diagnostics.
- [ ] Run and Tenant budgets stop all workers without losing already completed partial results.
- [ ] A failed worker reports to leader without silently escaping billing or cancellation rules.
- [ ] State-machine/unit and PostgreSQL + Redis integration tests pass 100%; changed code meets coverage gates.
