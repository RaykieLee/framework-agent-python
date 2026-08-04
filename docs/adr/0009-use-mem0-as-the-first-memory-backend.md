# Use Mem0 as the first long-term memory backend

The first AgentScope runtime uses Mem0 as the single backend for User Memory, with its user identifier derived from Tenant, User, and Agent Definition. ReMe is not enabled concurrently because its workspace-wide recall would introduce a second write-back, retrieval, and deletion model and make tenant-isolation evidence harder to establish. ReMe may be evaluated later through an explicit migration or memory-tier design rather than silently layering both systems.
