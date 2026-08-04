# Scope long-term memory by tenant, user, and agent definition

Long-term memory is included in the first AgentScope runtime and is keyed by Tenant, User, and Agent Definition. A leader and its workers may use that User Memory within the same Execution Team, but another member of the Organization cannot retrieve it. This gives Users useful cross-conversation continuity without creating an opaque organization-wide memory pool whose provenance, permissions, and deletion semantics would be difficult to control.
