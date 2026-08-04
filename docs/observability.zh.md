# 使用 Logfire 做可观测性

[Logfire](https://logfire.pydantic.dev) 是由 Pydantic 团队构建的现代可观测性平台。它对 Python 应用提供一流支持，尤其是那些使用 Pydantic、FastAPI 和 PydanticAI 的应用。

## 为什么选 Logfire?

- **为 Python 而生** —— 原生支持异步、类型提示和 Pydantic 模型
- **AI 优先** —— 与 PydanticAI 深度集成，提供智能体可观测性
- **兼容 OpenTelemetry** —— 可与任何 OTEL instrumentation 协作
- **界面美观** —— 现代化的控制台，具备强大的查询能力

## 支持的集成

### PydanticAI 智能体

对 AI 智能体的执行提供完整可见性：

```python
import logfire
from pydantic_ai import Agent

logfire.configure()
logfire.instrument_pydantic_ai()

agent = Agent("openai:gpt-4o-mini")

# 所有智能体运行都会被自动追踪
result = await agent.run("Hello!")
```

你在 Logfire 中能看到：
- 智能体运行的耗时和状态
- 工具调用及其参数与结果
- LLM 的请求与响应
- token 用量和成本
- 流式事件

### FastAPI

自动化的请求/响应追踪：

```python
from fastapi import FastAPI
import logfire

app = FastAPI()
logfire.configure()
logfire.instrument_fastapi(app)
```

你能看到：
- 请求方法、路径、状态码
- 请求/响应延迟
- 查询参数和请求头
- 出错时的异常详情

### 数据库

#### PostgreSQL(asyncpg)

```python
import logfire

logfire.instrument_asyncpg()
```

你能看到：
- 查询文本和参数
- 执行时间
- 行数
- 连接池统计

#### MongoDB(PyMongo/Motor)

```python
import logfire

logfire.instrument_pymongo()
```

你能看到：
- 集合操作
- 查询过滤器
- 执行时间
- 文档数量

### Redis

```python
import logfire

logfire.instrument_redis()
```

你能看到：
- 命令类型(GET、SET 等)
- 键模式
- 延迟
- 缓存命中/未命中模式

### 后台任务

#### Celery

```python
import logfire

logfire.instrument_celery()
```

你能看到：
- 任务名称和参数
- 执行时间
- worker 信息
- 重试次数
- 队列深度

#### Taskiq

```python
import logfire

logfire.instrument_taskiq()
```

### HTTP 客户端(HTTPX)

```python
import logfire

logfire.instrument_httpx()
```

你能看到：
- 请求 URL 和方法
- 响应状态码
- 延迟
- 请求/响应大小

## 配置

### 环境变量

```bash
# 必填
LOGFIRE_TOKEN=your-token-here

# 可选
LOGFIRE_PROJECT_NAME=my-project
LOGFIRE_ENVIRONMENT=production
LOGFIRE_SERVICE_VERSION=1.0.0
```

### 选择性 instrumentation

在生成器中，你可以选择对哪些组件做 instrumentation:

```bash
framework-agent-python new
# ✓ 启用 Logfire 可观测性
#   ✓ 对 FastAPI 做 instrumentation
#   ✓ 对数据库做 instrumentation
#   ✓ 对 Redis 做 instrumentation
#   ✓ 对 Celery 做 instrumentation
#   ✓ 对 HTTPX 做 instrumentation
```

### 生成的代码

启用 Logfire 后，你的 `app/main.py` 会包含：

```python
import logfire

# 配置 Logfire
logfire.configure()

# 根据你的选择做 instrumentation
logfire.instrument_fastapi(app)
logfire.instrument_asyncpg()  # 如果使用 PostgreSQL
logfire.instrument_pymongo()  # 如果使用 MongoDB
logfire.instrument_redis()    # 如果使用 Redis
logfire.instrument_celery()   # 如果使用 Celery
logfire.instrument_httpx()    # 如果启用了 HTTPX instrumentation
```

## 自定义 instrumentation

### 手动 span

为重要操作添加自定义 span:

```python
import logfire

async def process_order(order: Order):
    with logfire.span("process_order", order_id=str(order.id)):
        with logfire.span("validate"):
            await validate_order(order)

        with logfire.span("charge_payment"):
            await charge_payment(order)

        with logfire.span("send_confirmation"):
            await send_confirmation(order)
```

### 日志

Logfire 与 Python 的 logging 集成：

```python
import logfire

logfire.info("User registered", user_id=user.id, email=user.email)
logfire.warning("Rate limit approaching", current=95, limit=100)
logfire.error("Payment failed", order_id=order.id, error=str(e))
```

### 指标

追踪自定义指标：

```python
import logfire

# 计数器
logfire.metric_counter("orders_processed", 1, tags={"status": "success"})

# 仪表盘
logfire.metric_gauge("queue_depth", queue.size())

# 直方图
logfire.metric_histogram("response_time", latency_ms)
```

## 最佳实践

### 1. 使用结构化日志

```python
# 好的做法 —— 结构化数据
logfire.info("Order created", order_id=order.id, total=order.total)

# 避免 —— 字符串拼接
logfire.info(f"Order {order.id} created with total {order.total}")
```

### 2. 为 span 添加上下文

```python
with logfire.span("api_call",
    service="payment-gateway",
    operation="charge",
    amount=order.total
):
    result = await payment_api.charge(order)
```

### 3. 正确处理错误

```python
try:
    result = await risky_operation()
except Exception as e:
    logfire.exception("Operation failed", operation="risky")
    raise
```

### 4. 用标签做筛选

```python
logfire.info("Request processed",
    environment=settings.ENVIRONMENT,
    version=settings.VERSION,
    user_tier=user.subscription_tier
)
```

## 查看数据

### Logfire 控制台

在 [logfire.pydantic.dev](https://logfire.pydantic.dev) 访问你的追踪数据：

1. **实时追踪(Live Tail)** —— 实时日志流
2. **Trace 浏览器** —— 分布式 trace 可视化
3. **查询构建器** —— 对你的数据做类 SQL 查询
4. **仪表盘** —— 自定义可视化

### 示例查询

```sql
-- 慢的 API 端点
SELECT path, avg(duration_ms) as avg_latency
FROM spans
WHERE service = 'fastapi'
GROUP BY path
ORDER BY avg_latency DESC
LIMIT 10

-- 失败的 AI 智能体运行
SELECT *
FROM spans
WHERE span_name = 'agent.run'
  AND status = 'error'
ORDER BY timestamp DESC

-- 各模型的 token 用量
SELECT model, sum(tokens_used) as total_tokens
FROM spans
WHERE span_name LIKE 'llm.%'
GROUP BY model
```

## 疑难排查

### 没有数据出现

1. 检查 `LOGFIRE_TOKEN` 是否设置正确
2. 确认到 Logfire 的网络连通性
3. 检查日志中是否有初始化错误

### 缺少 span

1. 确保 instrumentation 在应用创建之后调用
2. 检查库版本是否兼容
3. 确认该组件确实正在被使用

### 高基数(high cardinality)警告

1. 避免在 span 名称中使用动态值
2. 对可变数据使用标签/属性
3. 对高吞吐端点考虑采样

## 资源

- [Logfire 文档](https://logfire.pydantic.dev/docs/)
- [集成指南](https://logfire.pydantic.dev/docs/integrations/)
- [PydanticAI 集成](https://logfire.pydantic.dev/docs/integrations/pydantic-ai/)
- [FastAPI 集成](https://logfire.pydantic.dev/docs/integrations/fastapi/)
- [OpenTelemetry 兼容性](https://logfire.pydantic.dev/docs/integrations/opentelemetry/)
