# 配置

生成项目时可用的全部选项。

## 核心选项

| 选项 | 取值 | 说明 |
|--------|--------|-------------|
| `--database` | `postgresql`、`none` | 异步 PostgreSQL(SQLAlchemy 2.0 + Alembic) |
| `--orm` | `sqlalchemy`、`sqlmodel` | ORM 选择(SQLModel 语法更简洁) |
| `--oauth-google` | 标志 | 启用 Google OAuth2 登录 |
| `--ai-framework` | `pydantic_ai`、`pydantic_deep`、`langchain`、`langgraph`、`deepagents` | AI 智能体框架 |
| `--llm-provider` | `openai`、`anthropic`、`google`、`openrouter` | LLM 服务商 |
| `--task-queue` | `none`、`celery`、`taskiq`、`arq` | 后台任务队列(基于 Redis)。**Prefect** 通过交互式向导提供。 |
| `--frontend` | `none`、`nextjs` | 前端框架 |

## 预设

```bash
# 完整生产配置
fastapi-fullstack create my_app --preset production

# 带流式输出的 AI 智能体
fastapi-fullstack create my_app --preset ai-agent

# 最简项目
fastapi-fullstack create my_app --minimal
```

## AI 框架选项

| 框架 | 服务商 | 说明 |
|-----------|-----------|-------------|
| `pydantic_ai` | OpenAI、Anthropic、Google、OpenRouter | 类型安全的智能体，内置 WebSearch/WebFetch |
| `pydantic_deep` | OpenAI、Anthropic、Google | 深度编程助手(文件系统工具、Docker/Daytona 沙箱) |
| `langchain` | OpenAI、Anthropic、Google | 功能全面的、基于链的智能体 |
| `langgraph` | OpenAI、Anthropic、Google | 基于图的 ReAct 智能体 |
| `deepagents` | OpenAI、Anthropic、Google | 支持子智能体委派的智能体框架 |

```bash
fastapi-fullstack create my_app --ai-framework pydantic_ai --llm-provider openai
fastapi-fullstack create my_app --ai-framework pydantic_deep --llm-provider anthropic
fastapi-fullstack create my_app --ai-framework langgraph --llm-provider google
```

## 数据库选项

### PostgreSQL

```bash
fastapi-fullstack create my_app --database postgresql
```

- 通过 `asyncpg` 实现异步
- SQLAlchemy 2.0 + Alembic 迁移
- 连接池
- 开箱支持 pgvector(可直接用作你的 RAG 向量库)

> PostgreSQL 是唯一支持的数据库。若要生成不带任何数据库的项目(例如无状态服务),请传 `--database none` —— 注意 JWT 认证、RAG 和团队功能都需要数据库。

## 后台任务选项

| 队列 | 说明 |
|-------|-------------|
| `celery` | 经典、久经考验(Redis broker) |
| `taskiq` | 异步原生、现代(Redis broker) |
| `arq` | 轻量级异步(Redis) |
| `prefect` | 工作流编排 —— 自托管服务器 + runner,支持 cron/间隔定时流程，Web UI 在 `:4200`。设置 `PREFECT_API_KEY` 可使用 Prefect Cloud |

```bash
# celery / taskiq / arq 通过 create 标志指定
fastapi-fullstack create my_app --task-queue celery --redis

# Prefect 通过交互式向导选择
fastapi-fullstack
```

## 消息渠道

通过交互式向导(`fastapi-fullstack new`)启用 Telegram 和/或 Slack 的多机器人集成。

| 平台 | 模式 | 特性 |
|----------|------|---------|
| **Telegram** | 轮询(开发) | 通过 aiogram v3 Socket Mode 实现长轮询 |
| **Telegram** | Webhook(生产) | `POST /telegram/{bot_id}/webhook`,带 HMAC 校验 |
| **Slack** | Socket Mode(开发) | 用于开发的 `slack-sdk` Socket Mode |
| **Slack** | Events API(生产) | `POST /slack/{bot_id}/events`,带 HMAC-SHA256 签名 |

两个平台共享同一套底层基础设施：

- **多机器人** —— 每个平台支持多个机器人，各自带有加密的令牌存储(Fernet)
- **按会话(session)隔离** —— Telegram 回复 + Slack thread_ts 各自拥有独立的 `ChannelSession`
- **群组并发控制** —— 每个聊天一个 `asyncio.Lock`,防止群聊中智能体调用交错
- **访问策略** —— `open`、`whitelist`、`jwt_linked`、`group_only`
- **命令** —— `/start`、`/new`、`/help`、`/link`、`/unlink`
- **身份关联** —— 通过一次性关联码将 Telegram/Slack 用户连接到应用账号

### 环境变量(Telegram)

```bash
TELEGRAM_WEBHOOK_BASE_URL=https://yourdomain.com  # 用于 webhook 模式
CHANNEL_ENCRYPTION_KEY=...  # 用于令牌存储的 Fernet 密钥
```

### 环境变量(Slack)

```bash
SLACK_SIGNING_SECRET=...    # 来自 Slack 应用设置(Events API 校验)
SLACK_BOT_TOKEN=xoxb-...    # 机器人 OAuth 令牌(用于发送消息)
SLACK_APP_TOKEN=xapp-...    # 应用级令牌(用于 Socket Mode 开发)
CHANNEL_ENCRYPTION_KEY=...  # 用于令牌存储的 Fernet 密钥
```

## 集成

在项目生成时启用：

```bash
fastapi-fullstack new
# ✓ Redis(缓存/会话)
# ✓ 限流(slowapi)
# ✓ 分页
# ✓ 管理后台(SQLAdmin)
# ✓ Webhooks
# ✓ Telegram 集成
# ✓ Slack 集成
# ✓ Sentry
# ✓ Logfire / LangSmith
# ✓ Prometheus
```

## 环境变量

生成的项目使用 `.env` 文件：

```bash
# 数据库
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/db

# 认证
JWT_SECRET_KEY=your-secret-key
JWT_ALGORITHM=HS256

# AI
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=...

# 消息渠道(如已启用)
CHANNEL_ENCRYPTION_KEY=...           # Fernet 密钥： python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
TELEGRAM_WEBHOOK_BASE_URL=https://...  # 仅 Telegram webhook 模式
SLACK_SIGNING_SECRET=...             # Slack Events API 签名校验
SLACK_BOT_TOKEN=xoxb-...             # Slack Web API
SLACK_APP_TOKEN=xapp-...             # Slack Socket Mode(仅开发)

# 可观测性
LOGFIRE_TOKEN=...
SENTRY_DSN=...
```

## 后续步骤

- [快速开始](quick-start.zh.md) - 运行你的项目
- [AI 智能体](../ai-agent.zh.md) - 配置 AI 框架
- [部署](../deployment.zh.md) - 部署到生产环境
