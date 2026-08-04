# 05 — Retrieve Control Plane Knowledge Bases through AgentScope

**What to build:** A user-selected Knowledge Base remains owned and ingested by the Control Plane while AgentScope retrieves authorized content with citations and mandatory Tenant/KB filtering.

**Blocked by:** 04 — Resume durable AgentScope sessions across processes.

**Status:** ready-for-human

- [ ] No second AgentScope KB CRUD or ingestion path is introduced.
- [ ] Personal, organization, and Platform Resource scopes resolve only within the Active Tenant rules.
- [ ] Real vector-store tests prove zero cross-Tenant or cross-KB leakage, including forged IDs and filters.
- [ ] Unit, integration, and grounded GLM evaluation pass 100% for security assertions; changed code meets coverage gates.

## Verification

- Generated AgentScope + Teams + RAG project includes the read-only adapter and contract tests.
- Adapter contract smoke: 6 passed (authorized personal/org resources, platform marker, forged/cross-tenant IDs, missing metadata, read-only lifecycle).
- Generator regression: `5 passed` (`tests/test_template_integration.py -k 'agentscope_kb or agentscope'`).
- AgentScope configuration regression: `3 passed` (`tests/test_config.py -k agentscope`).
- Generated adapter Ruff and compile checks passed; `ty` reports only pre-existing RAG/Qdrant warnings.
- PostgreSQL/Qdrant boundary test is marked `integration` and runs when `AGENTSCOPE_INTEGRATION_DATABASE_URL` and `AGENTSCOPE_INTEGRATION_QDRANT_URL` are supplied; local Docker image pulls were unavailable.
- GLM evaluation is intentionally not run in this slice; no credentials are stored in the repository.
