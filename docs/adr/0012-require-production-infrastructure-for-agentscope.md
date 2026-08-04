# Require PostgreSQL, Redis, and persistent Qdrant for AgentScope

Selecting the AgentScope execution runtime requires PostgreSQL for product and execution state, Redis for the MessageBus, event replay and distributed locks, and persistent Qdrant for Mem0 User Memory. In-process storage and message buses are permitted only in tests and are not generated as a deployment profile. This raises the minimum operational footprint, but avoids presenting non-durable single-process components as compatible with strict multi-tenancy and distributed teams.
