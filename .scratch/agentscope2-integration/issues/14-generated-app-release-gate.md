# 14 — Verify the complete generated AgentScope application

**What to build:** The generator's AgentScope configuration produces a demonstrable application covering chat, durable sessions, KB, User Memory, Personal Connections, Execution Team, billing, cleanup, and Tenant Purge without modifying AgentScope upstream.

**Blocked by:** 03 — Add deterministic and GLM-5.2 runtime evaluation; 10 — Apply AgentScope Delegated Authority to workers; 11 — Aggregate Team Run billing and stop propagation; 13 — Complete Tenant Purge across all stores.

**Status:** ready-for-agent

- [ ] Generated backend and frontend pass lint, type-check, unit, integration, and E2E suites.
- [ ] Python 3.11, 3.12, and 3.13 generation matrix passes 100% for supported combinations.
- [ ] Docker-backed PostgreSQL, Redis, Qdrant journey passes 100% with zero cross-Tenant leaks.
- [ ] GLM live evaluation reaches ≥90% semantic pass and 100% safety/isolation pass without secrets in artifacts.
