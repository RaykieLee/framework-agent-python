# Keep the knowledge lifecycle in the control plane

The Control Plane remains the sole authority for knowledge-base creation, ingestion, indexing, authorization, and deletion. AgentScope receives only server-resolved retrieval capabilities through a tool or RAG adapter and does not expose a second knowledge CRUD or ingestion path. This delays direct use of AgentScope's native knowledge APIs, but prevents duplicated vectors, inconsistent deletion, and authorization drift.
