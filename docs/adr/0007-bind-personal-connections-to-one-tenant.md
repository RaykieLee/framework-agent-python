# Bind each personal connection to one tenant

External-service credentials remain owned by the individual User, and workers may use the initiating User's connections through AgentScope's native delegation behavior. Each Personal Connection is additionally bound to one Tenant, and runtime resolution requires both its owner and the Active Tenant to match. A User must create or authorize a separate connection for another Tenant; this extra consent and schema complexity prevents one credential record from silently bridging mutually untrusted organizations.
