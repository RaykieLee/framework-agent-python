# Treat organizations as mutually untrusted tenants

Every Organization is a Tenant and must remain isolated even if an identifier is leaked or an application-layer query is incorrect. Isolation is enforced in depth with PostgreSQL row-level security, tenant-prefixed Redis state, mandatory tenant filters in vector retrieval, isolated workspaces, and cross-tenant negative tests. This increases infrastructure and migration complexity, but application repository filters alone are not an acceptable security boundary for unrelated SaaS customers.
