# Integrate AgentScope without a private fork

The AgentScope repository remains unmodified and the generated platform integrates it only through public extension points such as SubAgentTemplate, middleware, tool factories, ResourceAccessPolicy, and storage or knowledge adapters. Missing upstream capabilities are handled through independent upstream issues or pull requests rather than a template-owned fork. This may delay features that require upstream changes, but preserves upgradeability and keeps responsibility for AgentScope behavior with its maintainers.
