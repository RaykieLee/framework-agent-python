# 10 — Apply AgentScope Delegated Authority to workers

**What to build:** Workers follow AgentScope's native inheritance semantics for permission mode, allow/deny/ask rules, working directories, and eligible Personal Connections within the same Execution Team and Active Tenant.

**Blocked by:** 07 — Create single-Tenant Personal Connections; 09 — Dynamically form a single-level Execution Team.

**Status:** ready-for-agent

- [ ] SubAgentTemplate inheritance flags and precedence are preserved.
- [ ] Template rules override inherited rules where AgentScope specifies precedence; denied tools never execute.
- [ ] Workers cannot see credentials, directories, or resources outside the Active Tenant.
- [ ] Permission, MCP, HITL, and cross-Tenant negative tests pass 100%; changed code meets coverage gates.
