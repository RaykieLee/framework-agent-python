{%- if cookiecutter.use_agentscope %}
"""AgentScope execution seam used by the product WebSocket adapter.

Only this module knows how to construct AgentScope's native ``Agent`` and
``Msg`` objects.  The API route and the control plane consume the small
``stream`` seam below, so AgentScope can be replaced without leaking native
objects into the product API.
"""

from collections.abc import AsyncIterator, Callable
from typing import Any

from agentscope.agent import Agent
from agentscope.credential import OpenAICredential
from agentscope.event import AgentEvent
from agentscope.message import Msg, TextBlock
from agentscope.model import OpenAIChatModel

from app.agents.prompts import DEFAULT_SYSTEM_PROMPT
from app.core.config import settings


AgentFactory = Callable[[], Agent]


def _build_model(model_name: str) -> OpenAIChatModel:
    """Build an OpenAI-compatible AgentScope model from environment settings."""
    parameters = OpenAIChatModel.Parameters(
        temperature=settings.AI_TEMPERATURE,
        thinking_enable=settings.AI_THINKING_ENABLED,
        reasoning_effort=(settings.AI_THINKING_EFFORT if settings.AI_THINKING_ENABLED else None),
    )
    return OpenAIChatModel(
        credential=OpenAICredential(api_key=settings.OPENAI_API_KEY),
        model=model_name,
        parameters=parameters,
        stream=True,
    )


def _build_native_agent(model_name: str) -> Agent:
    """Construct one native AgentScope agent for a WebSocket conversation."""
    return Agent(
        name="assistant",
        system_prompt=DEFAULT_SYSTEM_PROMPT,
        model=_build_model(model_name),
    )


class AgentScopeAssistant:
    """Small, injectable wrapper around AgentScope's public ``Agent`` API."""

    def __init__(
        self,
        *,
        model_name: str | None = None,
        agent_factory: AgentFactory | None = None,
    ) -> None:
        self.model_name = model_name or settings.AI_MODEL
        self._agent = (agent_factory or (lambda: _build_native_agent(self.model_name)))()

    @property
    def agent(self) -> Agent:
        """Return the native agent for advanced adapters and tests."""
        return self._agent

    async def stream(
        self,
        user_message: str,
        *,
        continuation: Any | None = None,
    ) -> AsyncIterator[AgentEvent | Msg]:
        """Stream a user turn or a native HITL continuation.

        AgentScope owns conversation context on the ``Agent`` instance.  A
        session therefore sends only the new user ``Msg`` for a normal turn;
        continuation events are passed through unchanged.
        """
        inputs: Any
        if continuation is not None:
            inputs = continuation
        else:
            inputs = Msg(
                name="user",
                role="user",
                content=[TextBlock(text=user_message)],
            )
        async for event in self._agent.reply_stream(inputs, yield_final_msg=True):
            yield event


def get_agent(
    *,
    model_name: str | None = None,
    agent_factory: AgentFactory | None = None,
) -> AgentScopeAssistant:
    """Build an injectable AgentScope assistant for one conversation."""
    return AgentScopeAssistant(model_name=model_name, agent_factory=agent_factory)
{%- else %}
"""AgentScope is not selected."""
{%- endif %}
