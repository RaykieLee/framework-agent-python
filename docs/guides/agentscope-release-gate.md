# AgentScope generated-app release gate

The release gate renders one production-baseline project with the template as
the control plane and AgentScope as the internal execution runtime. It enables
PostgreSQL, Redis, persistent Qdrant, multi-tenant teams, billing/credits,
Next.js, and the AgentScope seams delivered in tickets 01–13. It does not
modify or fork AgentScope.

Run the deterministic generation matrix from the repository root:

```bash
uv run python scripts/agentscope_release_gate.py --json
```

The matrix renders Python 3.11, 3.12, and 3.13 configurations and checks:

- all runtime/control-plane seams (chat, durable session, KB, User Memory,
  Agent Definitions, Execution Team, delegated authority, Team Run billing,
  member exit, and Tenant Purge);
- PostgreSQL, Redis, Qdrant, and the AgentScope production extras;
- absence of native AgentScope service routes in product APIs;
- environment-only credentials and the generated frontend quality commands;
- backend line/branch and frontend changed-module coverage policy.

The report is redaction-safe and returns a non-zero exit code on a failed
static gate. `--no-matrix` is useful for a quick local check.

## Required test boundaries

The generated application publishes these commands. Run them from its
`backend/` and `frontend/` directories after installing dependencies:

```bash
# backend unit/contract tests (no external services)
uv run pytest -q tests/test_agentscope_\*.py -m 'not integration'

# backend integration boundary (requires all three URLs)
AGENTSCOPE_INTEGRATION_DATABASE_URL=... \
AGENTSCOPE_INTEGRATION_REDIS_URL=... \
AGENTSCOPE_INTEGRATION_QDRANT_URL=... \
uv run pytest -q tests/test_agentscope_\*.py -m integration

# complete backend suite and coverage
uv run pytest -q
uv run pytest -q --cov=app --cov-branch --cov-report=term-missing

# frontend lint, type-check, unit, and E2E
npm run lint
npm run type-check
npm run test:run -- --coverage
npm run test:e2e
```

The release policy is at least 90% changed backend line coverage and 85%
branch coverage. Existing frontend Vitest thresholds remain 100% for changed
modules. Integration tests are reported as skipped when service URLs are not
provided; a skip is never counted as a pass.

## Docker boundary

Docker is opt-in because pulling images and starting services changes local
runtime state:

```bash
uv run python scripts/agentscope_release_gate.py --docker --no-matrix
```

The gate validates compose, then attempts `db`, `redis`, and `qdrant`. If the
daemon is unavailable or an image cannot be pulled, it reports `SKIP` with a
reason and exits without deleting volumes or touching unrelated containers.

## Optional GLM evaluation

The generated evaluator is deterministic by default. A live GLM-5.2 run is
never automatic and reads its key only from the environment:

```bash
export AGENTSCOPE_EVAL_ENABLED=true
export AGENTSCOPE_EVAL_API_KEY='...'
uv run python scripts/agentscope_release_gate.py --glm --no-matrix
```

The quality gate requires semantic ≥90%, safety 100%, and tenant-isolation
100%. Do not put a key in source, `.env.example`, fixtures, CI logs, or the
release report. Rotate any credential that was pasted into chat or a shell
history before running a real evaluation.
