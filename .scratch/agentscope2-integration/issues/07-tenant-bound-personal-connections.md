# 07 — Create single-Tenant Personal Connections

**What to build:** MCP/OAuth connections remain personally owned but are bound to one Tenant; workers can use only the initiating User's connection in the same Active Tenant.

**Blocked by:** 02 — Complete single-Agent AgentScope chat.

**Status:** ready-for-agent

- [ ] Connection create, authorize, rotate, revoke, and list operations enforce owner plus Tenant.
- [ ] OAuth and bearer secrets remain encrypted, redacted, and absent from model prompts/logs.
- [ ] Mock-provider integration tests cover refresh, revocation, wrong-Tenant denial, and worker resolution.
- [ ] Unit/integration tests pass 100%; changed code meets coverage gates.
