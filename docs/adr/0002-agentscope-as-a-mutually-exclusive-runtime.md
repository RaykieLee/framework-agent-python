# Offer AgentScope as a mutually exclusive execution runtime

AgentScope is added to the generator as a sixth execution runtime and is mutually exclusive with PydanticAI, Pydantic Deep, LangChain, LangGraph, and DeepAgents. Treating it as an orchestration layer above any existing runtime would create two competing agent lifecycles, tool registries, and event models; a single runtime selection keeps generated applications understandable and independently installable.
