<h1 align="center">Full-Stack AI Agent Template</h1>
<p align="center">
  <em>生产就绪的 AI/LLM 应用 —— 几分钟，而非几周</em>
</p>
<p align="center">
  <a href="https://github.com/vstorm-co/framework-agent-python/actions/workflows/ci.yml"><img src="https://github.com/vstorm-co/framework-agent-python/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://codecov.io/gh/vstorm-co/framework-agent-python"><img src="https://img.shields.io/badge/coverage-100%25-brightgreen" alt="Coverage"></a>
  <a href="https://pypi.org/project/framework-agent-python/"><img src="https://img.shields.io/pypi/v/framework-agent-python.svg" alt="PyPI"></a>
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13-blue" alt="Python"></a>
  <a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/license-MIT-green" alt="License"></a>
</p>

---

**Full-Stack AI Agent Template** 是一个面向 AI/LLM 应用的生产就绪项目生成器，内置 25+ 项企业级集成。基于 FastAPI、Next.js 15 和你选择的 AI 框架构建。以 `framework-agent-python` CLI 的形式安装。

生成完整、类型安全的应用，自带认证、WebSocket 流式输出、可观测性和部署配置 —— 全部在几分钟内完成。

## 为什么选择这套脚手架？

1. **AI 优先设计**:原生支持 PydanticAI、LangChain、LangGraph、DeepAgents,具备 WebSocket 流式输出和会话持久化。

2. **生产就绪**:100% 测试覆盖率、严格类型、Docker/Kubernetes 配置，并在真实应用中经受过考验。

3. **25+ 项集成**:PostgreSQL、Redis、Celery/Prefect、Logfire、Sentry、Prometheus、Stripe、S3 等等 —— 全部可选、可配置。

4. **对 AI 智能体友好**:生成的项目包含针对 AI 编程助手优化的 `CLAUDE.md` 和 `AGENTS.md` 文件。

## 快速开始

```bash
# 1. 安装生成器
uv tool install framework-agent-python    # 或者： pipx install / pip install

# 2. 生成你的项目(交互式向导)
framework-agent-python

# 3. 后端 + PostgreSQL 启动，迁移已执行，管理员已初始化
cd my_app && make bootstrap

# 4. 前端(第二个终端)
cd frontend && bun install && bun dev
```

详见[快速开始指南](guides/quick-start.zh.md),以及[安装页面](installation.zh.md)中的预设和非交互式参数。

## 支持的 AI 框架

| 框架 | 流式输出 | 可观测性 | 服务商 |
|-----------|:---------:|:-------------:|:---------:|
| **PydanticAI** | WebSocket | Logfire | OpenAI、Anthropic、OpenRouter |
| **LangChain** | WebSocket | LangSmith | OpenAI、Anthropic |
| **LangGraph** | WebSocket | LangSmith | OpenAI、Anthropic |

## 核心特性

| 特性 | 说明 |
|---------|-------------|
| **AI 智能体** | PydanticAI、LangChain、LangGraph、DeepAgents,支持工具调用 |
| **WebSocket 流式输出** | 实时响应，可完整访问事件流 |
| **认证** | JWT + 刷新令牌、API 密钥、OAuth2(Google) |
| **数据库** | PostgreSQL(异步，SQLAlchemy 2.0 + Alembic) |
| **后台任务** | Celery、Taskiq、ARQ 或 Prefect |
| **可观测性** | Logfire、LangSmith、Sentry、Prometheus |
| **管理后台** | SQLAdmin,带认证 |
| **部署** | Docker、Kubernetes、GitHub Actions、GitLab CI |

## 生成的项目结构

```
my_project/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI 应用
│   │   ├── api/routes/v1/       # 版本化端点
│   │   ├── agents/              # AI 智能体
│   │   ├── services/            # 业务逻辑
│   │   └── repositories/        # 数据访问
│   ├── cli/                     # Django 风格命令
│   └── tests/
├── frontend/
│   ├── src/
│   │   ├── app/                 # Next.js App Router
│   │   ├── components/          # React 组件
│   │   └── hooks/               # useChat, useWebSocket
│   └── e2e/                     # Playwright 测试
├── docker-compose.yml
└── Makefile
```

## 相关项目

要构建高级 AI 智能体？看看 [pydantic-deep](https://github.com/vstorm-co/pydantic-deepagents) —— 一个具备规划、文件系统和子智能体能力的深度智能体框架。

## 后续步骤

- [安装](installation.zh.md) - 几分钟内开始
- [快速开始](guides/quick-start.zh.md) - 创建你的第一个项目
- [架构](architecture.zh.md) - 了解项目结构
- [AI 智能体](ai-agent.zh.md) - 配置 AI 框架
