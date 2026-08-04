# 01 — Generate a production-baseline AgentScope project

**What to build:** Selecting AgentScope in the generator produces an installable project with PostgreSQL, Redis, and persistent Qdrant prerequisites, without modifying or forking AgentScope.

**Blocked by:** None — can start immediately.

**Status:** ready-for-human

- [ ] CLI/config/cookiecutter generation supports AgentScope as the sixth mutually exclusive runtime.
- [ ] Invalid infrastructure combinations are rejected with actionable messages.
- [ ] Generated backend installs and passes ruff, ty, and its targeted tests.
- [ ] Generator unit/integration tests pass 100%; changed generator code meets ≥90% line and ≥85% branch coverage.

## Verification

- AgentScope config and generation tests: `3 passed` and `4 passed` (100%).
- Real CLI generation completed with PostgreSQL + Redis + Docker + Qdrant; generated backend dependency sync completed with AgentScope 2.0.5.
- Generated backend `ruff check .`: passed.
- Generated backend `ty check`: exit 0 with 15 pre-existing template diagnostics in RAG code; no AgentScope scaffold diagnostic.
- Generated backend import smoke test for `AgentScopeAssistant`: passed.
- Full generated backend pytest collection is currently blocked by an existing FastAPI/fastapi-pagination incompatibility (`get_body_field(..., body_params)`), not by the AgentScope baseline.
- Docker image pull was attempted, but the local Docker daemon hung while pulling images; no containers were started.
