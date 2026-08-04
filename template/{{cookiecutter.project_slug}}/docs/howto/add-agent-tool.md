# 如何：添加新的 Agent 工具

### 概述

Agent tools let your AI agent perform actions — search the web, query databases, send emails, etc. Each tool is a Python function that the agent can call.

### 分步指南

### 1. 创建工具文件

```python
# app/agents/tools/weather.py
{%- if cookiecutter.use_pydantic_ai %}
# PydanticAI tools are async functions decorated at registration time
async def get_weather(city: str) -> str:
    """Get current weather for a city.

    Args:
        city: Name of the city to get weather for.

    Returns:
        Weather description string.
    """
    # Your implementation here (API call, etc.)
    import httpx
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"https://wttr.in/{city}?format=3")
        return resp.text
{%- elif cookiecutter.use_langchain or cookiecutter.use_langgraph %}
from langchain_core.tools import tool

@tool
def get_weather(city: str) -> str:
    """Get current weather for a city."""
    import httpx
    resp = httpx.get(f"https://wttr.in/{city}?format=3")
    return resp.text
{%- endif %}
```

### 2. 在 `app/agents/tools/__init__.py`

```python
from app.agents.tools.weather import get_weather
```

### 3. 在 Agent 中注册

{%- if cookiecutter.use_pydantic_ai %}

In `app/agents/assistant.py`, add the tool to the agent:

```python
@agent.tool
async def weather_tool(ctx: RunContext[Deps], city: str) -> str:
    """Get current weather for a city."""
    from app.agents.tools.weather import get_weather
    return await get_weather(city)
```
{%- elif cookiecutter.use_langchain or cookiecutter.use_langgraph %}

In your agent file, add to the tools list:

```python
from app.agents.tools.weather import get_weather

tools = [get_current_datetime, get_weather]  # Add your tool here
```
{%- endif %}

### 4. 测试

启动服务器并询问 Agent： "What's the weather in Warsaw?"

### 提示

- 保持工具专注 — one tool, one job
- 编写清晰的文档字符串 — the agent uses them to decide when to call your tool
- 优雅地处理错误 — return error messages as strings, don't raise exceptions
- 对于耗时的操作，考虑添加缓存
