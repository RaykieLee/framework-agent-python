# 07 — Create single-Tenant Personal Connections

**What to build:** MCP/OAuth connections remain personally owned but are bound to one Tenant; workers can use only the initiating User's connection in the same Active Tenant.

**Blocked by:** 02 — Complete single-Agent AgentScope chat.

**Status:** ready-for-human

- [ ] Connection create, authorize, rotate, revoke, and list operations enforce owner plus Tenant.
- [ ] OAuth and bearer secrets remain encrypted, redacted, and absent from model prompts/logs.
- [ ] Mock-provider integration tests cover refresh, revocation, wrong-Tenant denial, and worker resolution.
- [ ] Unit/integration tests pass 100%; changed code meets coverage gates.

## Verification

- Generated Teams + MCP focused suite: `54 passed` under asyncio; the full generated MCP suite was `84 passed` under asyncio. Eleven Trio failures are pre-existing asyncio-only code.
- Personal connection routes, repository/service access, OAuth, rotate, revoke, and runtime tool resolution all require owner + Active Tenant.
- Bearer/OAuth material remains encrypted at rest and redacted from response schemas; runtime receives only short-lived auth headers.
- Migration adds non-null organization binding and tenant/user/name uniqueness. Database integration was not run because local Docker image pulls stalled.
