# Keep the template as the control plane and AgentScope as an execution runtime

The generated application remains the sole authority for identity, organizations, authorization, conversations, billing, and knowledge ownership. AgentScope is integrated behind the application's existing APIs as a replaceable execution runtime for agents, workers, events, and tools; its native service APIs are not exposed to clients. This gives up some ready-made AgentScope service functionality in exchange for one security boundary and one source of truth for product data.
