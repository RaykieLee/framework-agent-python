# 14 — Verify the complete generated AgentScope application

**What to build:** The generator's AgentScope configuration produces a demonstrable application covering chat, durable sessions, KB, User Memory, Personal Connections, Execution Team, billing, cleanup, and Tenant Purge without modifying AgentScope upstream.

**Blocked by:** 03 — Add deterministic and GLM-5.2 runtime evaluation; 10 — Apply AgentScope Delegated Authority to workers; 11 — Aggregate Team Run billing and stop propagation; 13 — Complete Tenant Purge across all stores.

**Status:** ready-for-human

- [x] Generated backend and frontend publish lint, type-check, unit, integration, and E2E release commands; deterministic generated contracts are covered by the gate.
- [x] Python 3.11, 3.12, and 3.13 generation matrix renders and passes the static production gate.
- [x] Docker-backed PostgreSQL, Redis, Qdrant journey has an opt-in compose check with graceful daemon/image-pull skip reporting and no destructive volume cleanup.
- [x] GLM live evaluation is optional, environment-only, and enforces ≥90% semantic plus 100% safety/isolation thresholds without secrets in artifacts.

## Implementation notes

- `scripts/agentscope_release_gate.py` is the release entry point. It renders
  the production baseline with the template as control plane and AgentScope as
  an internal runtime; native AgentScope service routes are rejected.
- `tests/test_agentscope_release_gate.py` covers the baseline configuration,
  required test command contract, generation gate, and Docker skip boundary.
- `docs/guides/agentscope-release-gate.md` documents commands, coverage policy,
  integration environment variables, Docker behavior, and opt-in GLM usage.

## Verification

- `ruff check scripts/agentscope_release_gate.py tests/test_agentscope_release_gate.py`: pass
- `pytest tests/test_agentscope_release_gate.py -q`: 4 passed
- `python scripts/agentscope_release_gate.py --no-matrix --json`: 5/5 static checks passed
