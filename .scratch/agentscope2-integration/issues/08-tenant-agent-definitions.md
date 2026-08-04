# 08 — Enable curated Agent Definitions per Tenant

**What to build:** Platform-published, versioned Agent Definitions can be enabled by Tenant owners/admins; members can run enabled definitions and viewers remain read-only.

**Blocked by:** 02 — Complete single-Agent AgentScope chat.

**Status:** ready-for-human

- [ ] Definitions expose role, capabilities, limits, and version without allowing tenant prompt/tool/permission rewrites.
- [ ] Owner/admin/member/viewer behavior matches the approved glossary and ADRs.
- [ ] API and UI flows cover enable, disable, version change, and unauthorized mutation.
- [ ] Unit, PostgreSQL integration, and UI tests pass 100%; changed code meets coverage gates.

## Verification

- Generated Agent Definition contract tests: `8 passed`; generator assertion: `1 passed`.
- Platform catalog, Tenant binding, Owner/Admin enable-disable/version/limit overrides, member read access, and viewer mutation denial are implemented through Control Plane DTOs; private prompt/tool/KB internals are redacted from public responses.
- Ruff and compile checks passed; Ty exits 0 with 21 pre-existing template warnings.
- PostgreSQL migration is present but not executed because local Docker image pulls stalled; no AgentScope source changes.
