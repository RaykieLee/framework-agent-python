# CLAUDE.md

本文件为 Claude Code（claude.ai/code）在此仓库中处理代码时提供指导。

## 项目概述

**全栈 AI 代理模板** 是一个交互式 CLI 工具，用于生成生产就绪的 FastAPI + Next.js 项目，支持 AI 代理、RAG 以及 20+ 企业级集成。使用带有 Jinja2 条件语句的 Cookiecutter 模板。

## 命令

```bash
# 安装依赖
uv sync

# 运行测试
uv run pytest

# 运行单个测试
uv run pytest tests/test_file.py::test_name -v

# 代码检查和格式化
uv run ruff check . --fix
uv run ruff format .

# 类型检查
uv run ty check
```

## CLI 用法

```bash
# 交互式向导（默认）
framework-agent-python

# 快速创建项目
framework-agent-python create my_project --database postgresql

# 启用 RAG
framework-agent-python create my_project --ai-framework pydantic_ai --rag --database postgresql --task-queue celery

# 列出可用选项
framework-agent-python templates
```

## 架构

### 核心模块（`fastapi_gen/`）

- **cli.py** — 基于 Click 的 CLI：`new`（交互式，默认）、`create`（直接）、`templates`（列出选项）
- **config.py** — Pydantic 模型：`ProjectConfig`、枚举（`AIFrameworkType`、`LLMProviderType`、`VectorStoreType` 等）、验证、cookiecutter 上下文
- **prompts.py** — 基于 Questionary 的交互式提示 → `ProjectConfig`
- **generator.py** — Cookiecutter 调用和生成后消息

### 模板系统（`template/`）

```
template/
├── cookiecutter.json                    # 默认上下文（~120 个变量）
├── hooks/post_gen_project.py            # 生成后清理和格式化
└── {{cookiecutter.project_slug}}/
    ├── backend/
    │   ├── app/
    │   │   ├── main.py                  # FastAPI 应用（含生命周期）
    │   │   ├── api/                     # 路由、依赖、异常处理
    │   │   ├── core/                    # 配置、安全、中间件
    │   │   ├── db/                      # 模型、会话管理
    │   │   ├── schemas/                 # Pydantic 请求/响应模型
    │   │   ├── repositories/            # 数据访问层
    │   │   ├── services/                # 业务逻辑
    │   │   ├── agents/                  # AI 代理（5 个框架）
    │   │   ├── rag/                     # RAG 模块（4 个向量数据库、嵌入、源）
    │   │   │   └── connectors/          # 同步源连接器（Google Drive、S3）
    │   │   ├── commands/                # Django 风格的 CLI 命令
    │   │   └── worker/                  # 后台任务（Celery/Taskiq/ARQ）
    │   ├── cli/                         # 生成的项目 CLI
    │   └── alembic/                     # 数据库迁移（如使用 SQL 数据库）
    └── frontend/                        # Next.js 15（可选）
        └── src/
            ├── app/[locale]/            # i18n 路由页面（PL/EN）
            │   ├── (marketing)/         # 公开页面（首页、定价、博客、法律）
            │   ├── (auth)/              # 登录、注册、重置密码
            │   ├── chat/, kb/, settings/, admin/
            │   └── auth/magic-link/     # 魔法链接验证
            ├── components/
            │   ├── marketing/           # 英雄区、功能、定价、FAQ、CTA
            │   ├── legal/               # 隐私/条款/Cookie 内容（按语言）
            │   ├── auth/, chat/, kb/, settings/, dashboard/, admin/
            │   └── ui/                  # shadcn 风格的基础组件
            └── app/{icon,opengraph-image,manifest,robots,sitemap}.tsx
```

## 关键设计决策

- 5 个 AI 框架：PydanticAI、PydanticDeep、LangChain、LangGraph、DeepAgents
- 4 个 LLM 提供商：OpenAI、Anthropic、Google Gemini、OpenRouter
- 4 个向量数据库后端：Milvus、Qdrant、ChromaDB、pgvector
- 4 个嵌入提供商：OpenAI、Voyage、Gemini（多模态）、SentenceTransformers
- RAG 文档源：本地文件（CLI）、Google Drive、S3/MinIO
- 通过 CLI 和 API 上传进行文档导入
- 同步源：可配置的连接器（Google Drive、S3），支持定时同步
- 3 个 PDF 解析器：PyMuPDF、LiteParse、LlamaParse（通过环境变量运行时选择）
- 通过 LLM 视觉 API 进行图像描述（可选，自愿加入）
- LlamaParse 支持 130+ 文档格式
- Logfire 用于 PydanticAI 可观测性，LangSmith 用于 LangChain/LangGraph/DeepAgents
- 仓库 + 服务模式 — 路由从不包含直接数据库调用
- 始终需要数据库（PostgreSQL 异步、MongoDB 异步、SQLite 同步）
- 前端 i18n：PL + EN，通过 `next-intl`，带语言前缀的路由，长篇散文按语言使用 TSX
- 营销站点（由 `enable_marketing_site` 控制）：首页、定价、FAQ、博客、联系、法律
- 认证流程：密码 + JWT、密码重置、魔法链接登录、OAuth 就绪
- 用户范围的 API 密钥（`sk_<43>` 格式，前缀查找 + bcrypt 验证）
- 管理面板（由 `enable_admin_panel` 控制）：工作区统计、Stripe 事件浏览器
- SEO 默认值：`opengraph-image.tsx`、`icon.tsx`、`manifest.ts`、`robots.ts`、`sitemap.ts`

## 查找更多信息

- 模板变量：`template/cookiecutter.json`
- 生成后逻辑：`template/hooks/post_gen_project.py`
- 变量文档：`template/VARIABLES.md`

## Agent skills

### Issue tracker

任务使用 `.scratch/<feature>/issues/` 下的本地 Markdown 文件。详见 `docs/agents/issue-tracker.md`。

### Triage labels

使用默认五状态词汇。详见 `docs/agents/triage-labels.md`。

### Domain docs

使用根目录 `CONTEXT.md` 和 `docs/adr/` 的单上下文结构。详见 `docs/agents/domain.md`。
