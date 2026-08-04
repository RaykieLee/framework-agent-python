{%- if cookiecutter.use_agentscope %}
"""AgentScope runtime seam.

The full streaming execution adapter is added in the next integration slice;
this module keeps the generated AgentScope project importable today.
"""

from typing import Any


class AgentScopeAssistant:
    """Placeholder for the AgentScope execution adapter."""

    def __init__(self, *, model_name: str | None = None) -> None:
        self.model_name = model_name

    async def run(self, _user_message: str, **_kwargs: Any) -> str:
        """Run one turn once the AgentScope adapter is enabled."""
        raise NotImplementedError("AgentScope chat execution is not enabled in this baseline")


def get_agent(*, model_name: str | None = None) -> AgentScopeAssistant:
    """Build the generated project's AgentScope assistant seam."""
    return AgentScopeAssistant(model_name=model_name)
{%- else %}
"""AgentScope is not selected."""
{%- endif %}
