# 08 — Enable curated Agent Definitions per Tenant

**What to build:** Platform-published, versioned Agent Definitions can be enabled by Tenant owners/admins; members can run enabled definitions and viewers remain read-only.

**Blocked by:** 02 — Complete single-Agent AgentScope chat.

**Status:** ready-for-agent

- [ ] Definitions expose role, capabilities, limits, and version without allowing tenant prompt/tool/permission rewrites.
- [ ] Owner/admin/member/viewer behavior matches the approved glossary and ADRs.
- [ ] API and UI flows cover enable, disable, version change, and unauthorized mutation.
- [ ] Unit, PostgreSQL integration, and UI tests pass 100%; changed code meets coverage gates.
