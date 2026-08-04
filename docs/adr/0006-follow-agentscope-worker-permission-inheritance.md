# Follow AgentScope worker permission inheritance

Workers receive the leader's permission mode, confirmed allow/deny/ask rules, and working directories according to the inheritance flags on their published Agent Definition, with template rules retaining AgentScope's native precedence. We favor AgentScope's built-in delegation model so workers can continue approved work without repeatedly interrupting the User; all inherited authority still remains inside the same Execution Team and Active Tenant.
