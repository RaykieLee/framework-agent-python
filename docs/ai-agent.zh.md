# AI 智能体文档

本文档描述脚手架中可用的 AI 智能体集成。

## 概览

脚手架支持 5 种 AI 框架来构建智能体：

| 框架 | 说明 | 适用场景 |
|-----------|-------------|----------|
| **PydanticAI** | 类型安全的 AI,集成 Pydantic,内置 WebSearch/WebFetch | 简单智能体、类型安全、具备联网能力 |
| **PydanticDeep** | 深度智能体编程助手，带文件系统工具、Docker/Daytona 沙箱 | 代码生成、文件操作 |
| **LangChain** | 全面的 AI 工具生态 | 复杂链、众多集成 |
| **LangGraph** | 基于图的 ReAct 智能体 | 多步推理、工具循环 |
| **DeepAgents** | 支持子智能体委派的智能体框架 | 高级多步任务 |

在项目创建时选择你的框架：

```bash
fastapi-fullstack create my_project --ai-framework pydantic_ai   # default
fastapi-fullstack create my_project --ai-framework pydantic_deep
fastapi-fullstack create my_project --ai-framework langchain
fastapi-fullstack create my_project --ai-framework langgraph
fastapi-fullstack create my_project --ai-framework deepagents
```

---

## PydanticAI 智能体

默认智能体由 [PydanticAI](https://ai.pydantic.dev) 驱动，提供：

- 类型安全的 AI 交互
- 工具/函数调用支持
- WebSocket 流式响应
- 对话历史持久化
- Logfire 可观测性集成

---

## 架构

```
┌─────────────────────────────────────────────────────────────┐
│                      WebSocket Client                        │
│                (Frontend / External Client)                  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    WebSocket Endpoint                        │
│                  /api/v1/agent/ws                           │
│         Authentication, Message Routing, Streaming           │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    AssistantAgent                            │
│              PydanticAI Agent Wrapper                        │
│         Model Config, Tools, Streaming via iter()            │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      LLM Provider                            │
│                  OpenAI / Anthropic / etc.                   │
└─────────────────────────────────────────────────────────────┘
```

---

## 配置

### 环境变量

```bash
# Required
OPENAI_API_KEY=sk-...

# Optional
AI_MODEL=gpt-4o-mini        # Default model
AI_TEMPERATURE=0.7          # Response creativity (0.0-1.0)
```

### 设置

```python
# app/core/config.py
class Settings(BaseSettings):
    # AI Agent
    OPENAI_API_KEY: str = ""
    AI_MODEL: str = "gpt-4o-mini"
    AI_TEMPERATURE: float = 0.7
```

---

## 智能体实现

### AssistantAgent 类

```python
# app/agents/assistant.py
from dataclasses import dataclass, field
from typing import Any

from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.settings import ModelSettings

from app.core.config import settings


@dataclass
class Deps:
    """Dependencies for the agent.

    Passed to tools via RunContext.
    """
    user_id: str | None = None
    user_name: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class AssistantAgent:
    """Wrapper for PydanticAI agent with tool support."""

    def __init__(
        self,
        model_name: str | None = None,
        temperature: float | None = None,
        system_prompt: str = "You are a helpful assistant.",
    ):
        self.model_name = model_name or settings.AI_MODEL
        self.temperature = temperature or settings.AI_TEMPERATURE
        self.system_prompt = system_prompt
        self._agent: Agent[Deps, str] | None = None

    def _create_agent(self) -> Agent[Deps, str]:
        """Create and configure the PydanticAI agent."""
        model = OpenAIChatModel(
            self.model_name,
            provider=OpenAIProvider(api_key=settings.OPENAI_API_KEY),
        )

        agent = Agent[Deps, str](
            model=model,
            model_settings=ModelSettings(temperature=self.temperature),
            system_prompt=self.system_prompt,
        )

        self._register_tools(agent)
        return agent

    def _register_tools(self, agent: Agent[Deps, str]) -> None:
        """Register all tools on the agent."""

        @agent.tool
        async def current_datetime(ctx: RunContext[Deps]) -> str:
            """Get the current date and time."""
            from app.agents.tools import get_current_datetime
            return get_current_datetime()

    @property
    def agent(self) -> Agent[Deps, str]:
        """Get or create the agent instance."""
        if self._agent is None:
            self._agent = self._create_agent()
        return self._agent

    async def run(
        self,
        user_input: str,
        history: list[dict[str, str]] | None = None,
        deps: Deps | None = None,
    ) -> tuple[str, list[Any], Deps]:
        """Run agent and return output with tool events."""
        # Convert history to PydanticAI format
        model_history = self._convert_history(history or [])
        agent_deps = deps or Deps()

        result = await self.agent.run(
            user_input,
            deps=agent_deps,
            message_history=model_history,
        )

        # Extract tool call events
        tool_events = []
        for message in result.all_messages():
            if hasattr(message, "parts"):
                for part in message.parts:
                    if hasattr(part, "tool_name"):
                        tool_events.append(part)

        return result.output, tool_events, agent_deps

    async def iter(
        self,
        user_input: str,
        history: list[dict[str, str]] | None = None,
        deps: Deps | None = None,
    ):
        """Stream agent execution with full event access."""
        model_history = self._convert_history(history or [])
        agent_deps = deps or Deps()

        async with self.agent.iter(
            user_input,
            deps=agent_deps,
            message_history=model_history,
        ) as run:
            async for event in run:
                yield event
```

---

## 添加自定义工具

### 创建工具

```python
# app/agents/tools/weather.py
import httpx


async def get_weather(city: str) -> dict:
    """Get current weather for a city.

    Args:
        city: City name (e.g., "London", "New York")

    Returns:
        Weather data including temperature and conditions.
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://api.weatherapi.com/v1/current.json",
            params={"key": "YOUR_API_KEY", "q": city},
        )
        data = response.json()

    return {
        "city": city,
        "temperature": data["current"]["temp_c"],
        "condition": data["current"]["condition"]["text"],
        "humidity": data["current"]["humidity"],
    }
```

### 注册工具

```python
# app/agents/assistant.py

def _register_tools(self, agent: Agent[Deps, str]) -> None:
    """Register all tools on the agent."""

    @agent.tool
    async def current_datetime(ctx: RunContext[Deps]) -> str:
        """Get the current date and time."""
        from app.agents.tools import get_current_datetime
        return get_current_datetime()

    @agent.tool
    async def get_weather(ctx: RunContext[Deps], city: str) -> dict:
        """Get current weather for a city.

        Args:
            city: City name (e.g., "London", "New York")
        """
        from app.agents.tools.weather import get_weather as fetch_weather
        return await fetch_weather(city)

    @agent.tool
    async def search_database(ctx: RunContext[Deps], query: str) -> list[dict]:
        """Search the database for items.

        Args:
            query: Search query string
        """
        # Access dependencies via ctx.deps
        user_id = ctx.deps.user_id
        # Perform search...
        return results
```

### 工具最佳实践

1. **清晰的 docstring** —— LLM 靠它们判断何时调用工具
2. **类型标注** —— 参数校验所必需
3. **错误处理** —— 返回有意义的错误信息

---

## RAG 工具集成

启用 RAG 后，智能体可以在知识库中检索相关文档。

### 同时启用 RAG 与 AI 智能体

```bash
fastapi-fullstack create my_project --enable-rag --enable-ai-agent
```

### 使用 RAG 工具

```python
# app/agents/assistant.py
from app.agents.tools.rag_tool import search_knowledge_base

def _register_tools(self, agent: Agent[Deps, str]) -> None:
    """Register all tools on the agent."""

    @agent.tool
    async def search_knowledge(ctx: RunContext[Deps], query: str) -> str:
        """Search the knowledge base for relevant documents.
        
        Args:
            query: The search query string
        """
        return await search_knowledge_base(
            query=query,
            collection="documents",
            top_k=5
        )
```

### RAG 工具函数签名

```python
async def search_knowledge_base(
    query: str,
    collection: str = "documents",
    top_k: int = 5,
) -> str:
    """Search the knowledge base and return formatted results.
    
    Args:
        query: The search query string.
        collection: Name of the collection to search (default: "documents").
        top_k: Number of top results to retrieve (default: 5).
    
    Returns:
        Formatted string with search results, including content and scores.
    """
```

另见：[RAG 文档](rag.zh.md)了解详细配置。
3. **异步** —— I/O 操作使用异步函数
4. **错误处理** —— 返回对用户友好的错误信息
5. **上下文访问** —— 用 `ctx.deps` 获取用户特定数据

---

## WebSocket 端点

### 基础端点

```python
# app/api/routes/v1/agent.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic_ai.messages import PartDeltaEvent

from app.agents.assistant import AssistantAgent, Deps

router = APIRouter(prefix="/agent", tags=["agent"])


@router.websocket("/ws")
async def agent_websocket(websocket: WebSocket):
    """WebSocket endpoint for AI agent streaming."""
    await websocket.accept()

    agent = AssistantAgent()
    history: list[dict[str, str]] = []

    try:
        while True:
            # Receive message
            data = await websocket.receive_json()
            user_input = data.get("content", "")
            history = data.get("history", history)

            # Send start event
            await websocket.send_json({"type": "start"})

            # Stream response
            full_response = ""
            async for event in agent.iter(user_input, history):
                if isinstance(event, PartDeltaEvent):
                    if hasattr(event.delta, "content"):
                        token = event.delta.content
                        full_response += token
                        await websocket.send_json({
                            "type": "token",
                            "content": token,
                        })

                # Handle tool calls
                if hasattr(event, "tool_name"):
                    await websocket.send_json({
                        "type": "tool_call",
                        "tool": {
                            "name": event.tool_name,
                            "args": event.args,
                        },
                    })

            # Update history
            history.append({"role": "user", "content": user_input})
            history.append({"role": "assistant", "content": full_response})

            # Send end event
            await websocket.send_json({"type": "end"})

    except WebSocketDisconnect:
        pass
```

### 带认证

```python
# app/api/routes/v1/agent.py
from fastapi import WebSocket, WebSocketDisconnect, Query, HTTPException

from app.core.security import verify_token
from app.services.user import UserService


@router.websocket("/ws")
async def agent_websocket(
    websocket: WebSocket,
    token: str | None = Query(None),
):
    """WebSocket endpoint with JWT authentication."""
    # Verify token
    if not token:
        await websocket.close(code=4001, reason="Missing token")
        return

    payload = verify_token(token)
    if payload is None:
        await websocket.close(code=4001, reason="Invalid token")
        return

    await websocket.accept()

    # Create agent with user context
    deps = Deps(
        user_id=payload["sub"],
        user_name=payload.get("name"),
    )
    agent = AssistantAgent()

    # ... rest of the handler
```

---

## 对话持久化

### 数据库模型

```python
# app/db/models/conversation.py
from uuid import uuid4
from datetime import datetime

from sqlalchemy import String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.base import Base


class Conversation(Base):
    """Conversation (chat session) model."""

    __tablename__ = "conversations"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), onupdate=func.now())

    messages: Mapped[list["Message"]] = relationship("Message", back_populates="conversation")


class Message(Base):
    """Chat message model."""

    __tablename__ = "messages"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    conversation_id: Mapped[UUID] = mapped_column(ForeignKey("conversations.id"), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # user, assistant, tool
    content: Mapped[str] = mapped_column(Text, nullable=False)
    tool_calls: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    conversation: Mapped["Conversation"] = relationship("Conversation", back_populates="messages")
```

### 对话服务

```python
# app/services/conversation.py
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.conversation import Conversation, Message
from app.repositories.conversation import conversation_repo


class ConversationService:
    """Service for managing conversations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, user_id: UUID, title: str | None = None) -> Conversation:
        """Create a new conversation."""
        return await conversation_repo.create(self.db, user_id=user_id, title=title)

    async def add_message(
        self,
        conversation_id: UUID,
        role: str,
        content: str,
        tool_calls: dict | None = None,
    ) -> Message:
        """Add a message to a conversation."""
        return await conversation_repo.add_message(
            self.db,
            conversation_id=conversation_id,
            role=role,
            content=content,
            tool_calls=tool_calls,
        )

    async def get_messages(self, conversation_id: UUID) -> list[Message]:
        """Get all messages in a conversation."""
        return await conversation_repo.get_messages(self.db, conversation_id)
```

### 持久化消息

```python
# In WebSocket handler
async for event in agent.iter(user_input, history):
    # ... stream tokens ...

# Save to database
await conversation_service.add_message(
    conversation_id=conversation_id,
    role="user",
    content=user_input,
)
await conversation_service.add_message(
    conversation_id=conversation_id,
    role="assistant",
    content=full_response,
    tool_calls=tool_events if tool_events else None,
)
```

---

## Logfire 集成

智能体会被自动接入 Logfire 做 instrumentation:

```python
# app/core/logfire_setup.py
import logfire


def instrument_pydantic_ai() -> None:
    """Instrument PydanticAI for Logfire tracing."""
    logfire.instrument_pydantic_ai()
```

它提供：

- 每次智能体运行的 **trace**
- **token 用量**追踪
- **工具调用**可见性
- **延迟**指标
- **错误**追踪

在 [Logfire 控制台](https://logfire.pydantic.dev)查看 trace。

---

## 前端集成

### WebSocket Hook

```typescript
// src/hooks/use-websocket.ts
export function useAgentWebSocket() {
  const [isConnected, setIsConnected] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  const connect = useCallback((token?: string) => {
    const url = token
      ? `${WS_URL}?token=${token}`
      : WS_URL;

    const ws = new WebSocket(url);

    ws.onopen = () => setIsConnected(true);
    ws.onclose = () => setIsConnected(false);
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      handleMessage(data);
    };

    wsRef.current = ws;
  }, []);

  const send = useCallback((content: string, history: Message[]) => {
    wsRef.current?.send(JSON.stringify({
      type: 'message',
      content,
      history: history.map(m => ({
        role: m.role,
        content: m.content,
      })),
    }));
  }, []);

  return { isConnected, isStreaming, connect, send };
}
```

### 消息类型

```typescript
// src/types/chat.ts
interface StreamEvent {
  type: 'start' | 'token' | 'tool_call' | 'end' | 'error';
  content?: string;
  tool?: {
    name: string;
    args: Record<string, unknown>;
  };
  error?: string;
}

interface Message {
  id: string;
  role: 'user' | 'assistant' | 'tool';
  content: string;
  tool_name?: string;
  created_at: Date;
}
```

---

## 最佳实践

1. **系统提示词** —— 明确说明智能体的角色和能力
2. **工具设计** —— 保持工具聚焦、文档完善
3. **错误处理** —— 向用户返回优雅的错误信息
4. **限流** —— 用请求限额防止滥用
5. **上下文管理** —— 限制历史长度以控制 token 用量
6. **可观测性** —— 用 Logfire 监控智能体行为
7. **测试** —— 用模拟的 LLM 响应做确定性测试

---

## 疑难排查

### 常见问题

**"Invalid API key"**

- 检查 `OPENAI_API_KEY` 是否设置正确
- 确认该密钥有足够额度

**"Model not found"**

- 检查 `AI_MODEL` 是否是有效的模型名
- 确认你有权访问指定模型

**"WebSocket connection failed"**

- 确认后端正在运行
- 检查 WebSocket 连接的 CORS 设置
- 确认令牌有效(若使用认证)

**"Tool not found"**

- 确认工具已在 `_register_tools()` 中注册
- 检查工具的 docstring 是否足够具描述性

---

## LangGraph ReAct 智能体

[LangGraph](https://langchain-ai.github.io/langgraph/) 提供基于图的智能体编排，采用 ReAct 模式。

### 架构

```
┌─────────────────────────────────────────────────────────────┐
│                      WebSocket Client                        │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    WebSocket Endpoint                        │
│                  /api/v1/agent/ws                           │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   LangGraphAssistant                         │
│               Graph-based ReAct Agent                        │
│         Agent Node ←→ Tools Node (conditional loop)         │
└─────────────────────────────────────────────────────────────┘
```

### ReAct 模式

智能体遵循「推理 + 行动」模式：

1. **推理** —— 分析输入并决定行动
2. **行动** —— 如有需要则执行工具
3. **观察** —— 处理工具结果
4. **重复** —— 持续直到任务完成

### 配置

```python
# app/agents/langgraph_assistant.py
from langgraph.graph import StateGraph, MessagesState

class LangGraphAssistant:
    def __init__(self, model_name: str = "gpt-4o-mini"):
        self.model = ChatOpenAI(model=model_name)
        self.tools = [get_current_datetime]
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        graph = StateGraph(MessagesState)
        graph.add_node("agent", self._agent_node)
        graph.add_node("tools", self._tools_node)
        graph.add_conditional_edges(
            "agent",
            self._should_continue,
            {"continue": "tools", "end": END}
        )
        graph.add_edge("tools", "agent")
        graph.set_entry_point("agent")
        return graph.compile(checkpointer=MemorySaver())
```

### 流式模式

LangGraph 支持两种流式模式：

```python
# Token streaming (for LLM output)
async for event in assistant.stream(prompt, mode="messages"):
    if event["type"] == "token":
        print(event["content"], end="")

# State updates (for tool calls)
async for event in assistant.stream(prompt, mode="updates"):
    if event["type"] == "tool_call":
        print(f"Calling: {event['tool_name']}")
```

---

## 框架对比

| 特性 | PydanticAI | LangChain | LangGraph |
|---------|------------|-----------|-----------|
| 类型安全 | ✅ 原生 | ⚠️ 手动 | ⚠️ 手动 |
| 多智能体 | ❌ | ⚠️ 复杂 | ⚠️ 复杂 |
| 工具调用 | ✅ | ✅ | ✅ |
| 流式输出 | ✅ iter() | ✅ astream | ✅ astream |
| 记忆 | ✅ 内置 | ✅ 链 | ✅ Checkpointer |
| 复杂度 | 低 | 中 | 中 |
| 依赖 | 少 | 多 | 中 |

### 何时选择哪个

- **PydanticAI**:简单助手、聊天机器人、类型安全的应用
- **LangChain**:复杂链、需要大量第三方集成
- **LangGraph**:多步推理、工具循环、状态机
