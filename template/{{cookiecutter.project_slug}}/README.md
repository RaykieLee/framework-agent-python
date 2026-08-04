 # {{ cookiecutter.project_name }}
 
 {{ cookiecutter.project_description }}
 
 > 由 [全栈 AI Agent 模板](https://github.com/vstorm-co/framework-agent-python) 生成。

---

## Stack

 | 组件 | 技术 |
 |-----------|-----------|
 | **后端** | FastAPI + Pydantic v2 |
 | **数据库** | PostgreSQL（asyncpg 异步） |
 | **认证** | JWT + 刷新令牌{% if cookiecutter.use_api_key %} + API 密钥{% endif %}{% if cookiecutter.enable_oauth %} + OAuth{% endif %} |
{%- if cookiecutter.enable_redis %}
 | **缓存** | Redis |
{%- endif %}
 | **AI 框架** | {{ cookiecutter.ai_framework }}（{{ cookiecutter.llm_provider }}） |
{%- if cookiecutter.enable_rag %}
 | **RAG** | {{ cookiecutter.vector_store }} 向量数据库 |
{%- endif %}
{%- if cookiecutter.background_tasks != "none" %}
 | **任务队列** | {{ cookiecutter.background_tasks }} |
{%- endif %}
{%- if cookiecutter.use_frontend %}
 | **前端** | Next.js 15 + React 19 + Tailwind v4 |
{%- endif %}
{%- if cookiecutter.enable_billing %}
 | **计费** | Stripe |
{%- endif %}

---

 ## 前提条件
 
 | 工具 | 版本 | 安装方式 |
 |---|---|---|
 | **Docker** | Desktop / Engine 24+ | <https://docs.docker.com/get-docker/> |
 | **Make** | GNU Make 3.81+（macOS/Linux 预装） | Windows: 通过 [chocolatey](https://chocolatey.org/) `choco install make` 或使用 WSL2 |
 | **uv** | 最新版 | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
{%- if cookiecutter.use_frontend %}
 | **bun** | 1.x | `curl -fsSL https://bun.sh/install \| bash`（或使用 `npm` / `pnpm`） |
{%- endif %}

 > **Windows 用户：** Makefile 和 Shell 辅助脚本基于 bash。建议使用 **WSL2** 或 **Git Bash** 以获得最佳体验。下面的 Docker 工作流程在 macOS、Linux 和 WSL2 上完全一致。

---

 ## 快速开始（本地开发）
 
 ### 首次运行
 
 ```bash
 make bootstrap       # = make dev + make seed
 ```
 
 这是全新克隆后唯一需要的命令。之后日常工作只需 `make dev`。
 
 ### 后续运行
 
 ```bash
 make dev
 ```
 
 `make dev` 是**幂等的**——可随时重新运行。它会：
 
 1. 构建后端 Docker 镜像（首次运行后缓存）
 2. 通过 `docker-compose.dev.yml` 启动服务（含热重载绑定挂载）
 3. 轮询 PostgreSQL 直到接受连接（`pg_isready` — 无需固定等待时间）
 4. 应用待处理的 Alembic 迁移（如已是最新则无操作）
 
 它**不会**重新创建管理员用户——该操作在 `make seed` 中，仅运行一次。这样 `make dev` 在每次代码/配置更改后都能快速重新运行。
 
 **然后访问：**
 
 - API：<http://localhost:{{ cookiecutter.backend_port }}>
 - 文档：<http://localhost:{{ cookiecutter.backend_port }}/docs>
{%- if cookiecutter.use_jwt %}
 - 管理后台：<http://localhost:{{ cookiecutter.backend_port }}/admin> — `make seed` 后使用 `admin@example.com` / `admin123`
{%- endif %}
{%- if cookiecutter.use_frontend %}
 - 前端：<http://localhost:{{ cookiecutter.frontend_port }}> — 通过 `make dev-frontend`（Docker）或 `cd frontend && bun install && bun dev`（本地）启动
{%- endif %}

 ### 日常命令
 
 ```bash
 make dev           # 自举或重启（幂等，不会重新创建管理员）
{%- if cookiecutter.use_jwt %}
 make seed          # 一次性创建管理员（如已存在则无操作）
{%- endif %}
 make dev-down      # 停止所有服务
 make dev-logs      # 跟踪日志（Ctrl-C 退出）
 make dev-rebuild   # 强制重建后端镜像（pyproject.toml 变更后）
{%- if cookiecutter.use_frontend %}
 make dev-frontend  # 启动 Next.js 容器
{%- endif %}
```

 如果你更倾向于在主机上运行后端（而非 Docker）——适用于断点调试 / IDE 调试：

```bash
 make install       # uv sync + pre-commit 安装
 docker compose -f docker-compose.dev.yml up -d db{% if cookiecutter.enable_redis %} redis{% endif %}{% if cookiecutter.enable_rag %} milvus etcd minio{% endif %}
 make db-upgrade    # 应用迁移
 make run           # 本地运行 uvicorn，带 --reload
```

---

 ## 环境
 
 | `make` 目标 | Compose 文件 | 用途 |
 |---|---|---|
 | `make dev` | `docker-compose.dev.yml` | 本地开发，热重载 + 绑定挂载源码。 |
 | `make stage` | `docker-compose.yml` | 类似生产环境的构建，无绑定挂载，本地主机运行。部署前验证时使用。 |
 | `make prod` | `docker-compose.prod.yml` | 生产环境。需要 `backend/.env`（从 `backend/.env.example` 复制，填写真实密钥）和外部 Nginx（使用 `nginx/nginx.conf`）。 |

 每个环境都有对应的 `-down`、`-logs`、`-rebuild` 配套命令（例如 `make stage-down`）。

---

 ## 项目结构

```
backend/app/
 ├── main.py               # FastAPI 应用 + 生命周期
 ├── api/
 │   ├── deps.py           # 注解式 DI 别名（DBSession, CurrentUser, *Svc）
 │   ├── exception_handlers.py
 │   └── routes/v1/        # HTTP 端点——调用服务层，绝不直接调用仓库
 ├── core/
 │   ├── config.py         # pydantic-settings（读取 .env）
 │   ├── security.py       # JWT、bcrypt、API 密钥验证
 │   ├── exceptions.py     # AppException → NotFound / Auth 等
 │   └── middleware.py
 ├── db/
 │   ├── base.py           # DeclarativeBase + TimestampMixin
 │   └── models/           # SQLAlchemy 模型（Mapped[] 类型提示）
 ├── schemas/              # Pydantic v2: *Create / *Update / *Read / *List
 ├── repositories/         # 数据访问层——db.flush() 永不提交
 ├── services/             # 业务逻辑层——抛出领域异常
 ├── agents/               # AI Agent 封装 + 工具
{%- if cookiecutter.enable_rag %}
 ├── rag/                  # RAG：向量存储 + 嵌入 + 摄取 + 数据源
 │   └── connectors/       # 可插拔同步源连接器（Google Drive、S3 等）
{%- endif %}
{%- if cookiecutter.background_tasks != "none" %}
 ├── worker/
 │   ├── background/       # FastAPI BackgroundTasks 回退（进程内）
 │   └── tasks/            # 分布式任务（{{ cookiecutter.background_tasks }}）
{%- endif %}
 └── commands/             # Click CLI 命令（由 `{{ cookiecutter.project_slug }} cmd …` 自动发现）
{%- if cookiecutter.use_frontend %}

frontend/src/
 ├── app/
 │   ├── [locale]/         # next-intl 路由（en/pl）
{%- if cookiecutter.enable_marketing_site %}
 │   │   ├── (marketing)/  # 公开落地页、定价、FAQ、博客
{%- endif %}
 │   │   └── (dashboard)/  # 已认证应用
│   └── api/              # Server-side API proxies (forward auth cookies)
 ├── components/           # React 组件（聊天、营销、UI 基础组件）
 ├── hooks/                # useAuth、useChat、useConversations 等
 ├── stores/               # Zustand 状态管理
 └── lib/                  # api-client、server-api、工具函数
{%- endif %}
```

---

 ## CLI
 
 生成的项目附带一个 Click CLI，通过 `{{ cookiecutter.project_slug }}` 暴露（`make install` 后可用）：

```bash
 {{ cookiecutter.project_slug }} server run --reload          # 开发服务器
 {{ cookiecutter.project_slug }} db upgrade                   # 应用迁移
 {{ cookiecutter.project_slug }} db migrate -m "message"      # 创建新迁移
 {{ cookiecutter.project_slug }} user create-admin            # 交互式管理员创建
{%- if cookiecutter.enable_rag %}
 {{ cookiecutter.project_slug }} rag-ingest <path> -c docs    # 摄取本地文件
 {{ cookiecutter.project_slug }} rag-search "query" -c docs   # 语义搜索
 {{ cookiecutter.project_slug }} rag-collections              # 列出集合
{%- endif %}
{%- if cookiecutter.background_tasks == "celery" %}
 {{ cookiecutter.project_slug }} celery worker                # 启动 Worker
 {{ cookiecutter.project_slug }} celery beat                  # 启动调度器
{%- elif cookiecutter.background_tasks == "taskiq" %}
 {{ cookiecutter.project_slug }} taskiq worker                # 启动 Worker
 {{ cookiecutter.project_slug }} taskiq scheduler             # 启动调度器
{%- endif %}
```
{%- if cookiecutter.background_tasks == "prefect" %}

 后台任务运行在 **Prefect** 上——`prefect-server`（UI 地址 <http://localhost:4200>）和 `prefect-runner` 容器随 `make dev` 启动。Flow 位于 `app/worker/tasks/`，在 `app/worker/prefect_app.py` 中注册。
{%- endif %}

 运行 `make help` 查看分类列表，或 `{{ cookiecutter.project_slug }} --help` 查看完整 CLI 文档。

---

 ## 配置
 
 所有后端配置位于 `backend/.env`（开发默认值已提交）。关键变量：

```bash
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB={{ cookiecutter.project_slug }}
{%- if cookiecutter.use_openai %}

 # OpenAI — 聊天 + 嵌入所需
 OPENAI_API_KEY=sk-…
{%- endif %}
{%- if cookiecutter.use_anthropic %}
ANTHROPIC_API_KEY=sk-ant-…
{%- endif %}
{%- if cookiecutter.use_google %}
GOOGLE_API_KEY=…
{%- endif %}
{%- if cookiecutter.enable_oauth_google %}

 # Google OAuth（Google 登录）
 GOOGLE_CLIENT_ID=…
 GOOGLE_CLIENT_SECRET=…
{%- endif %}
{%- if cookiecutter.enable_billing %}

 # Stripe 计费
 STRIPE_SECRET_KEY=sk_test_…
 STRIPE_WEBHOOK_SECRET=whsec_…
{%- endif %}
{%- if cookiecutter.enable_email %}

 # 邮件（事务性邮件 + 生命周期）
 EMAIL_PROVIDER={{ cookiecutter.email_provider }}
{%- if cookiecutter.email_provider == "resend" %}
 RESEND_API_KEY=re_…
{%- endif %}
 EMAIL_FROM=noreply@your-domain.com
{%- endif %}
```

 查看 `backend/.env.example` 获取完整列表及注释。

 生产环境中，**切勿**提交密钥——`backend/.env` 已被 `.gitignore` 忽略。在服务器上填写真实值（或通过平台的密钥管理器注入：Doppler、AWS Secrets Manager、GitHub Actions Secrets 等）。开发和生产共用一个 `backend/.env`——没有独立的 `.env.prod`。

---

 ## 开发
 
 | 命令 | 功能 |
 |---|---|
 | `make test` | 运行 pytest |
 | `make lint` | 运行 ruff check + format check + ty |
 | `make format` | 使用 ruff 自动格式化 |
 | `make db-migrate` | 根据模型更改生成新迁移（交互式） |
 | `make db-upgrade` | 应用待处理的迁移 |
 | `make db-downgrade` | 回滚一个迁移 |
 | `make db-current` | 显示当前版本 |
{%- if cookiecutter.use_jwt %}
 | `make create-admin` | 交互式管理员创建 |
 | `make user-list` | 列出所有用户 |
{%- endif %}
{%- if cookiecutter.background_tasks == "celery" %}
 | `make celery-worker` | 本地运行 Celery Worker |
 | `make celery-beat` | 运行 Celery Beat |
 | `make celery-flower` | 打开 Flower UI（<http://localhost:5555>） |
{%- elif cookiecutter.background_tasks == "taskiq" %}
 | `make taskiq-worker` | 本地运行 Taskiq Worker |
 | `make taskiq-scheduler` | 运行 Taskiq 调度器 |
{%- elif cookiecutter.background_tasks == "prefect" %}
 | `make dev` | 启动 Prefect 服务器 + Runner（UI 地址 <http://localhost:4200>） |
{%- endif %}

---
{%- if cookiecutter.enable_rag %}

 ## RAG（知识库）
 
 使用 **{{ cookiecutter.vector_store }}** 作为向量存储，**{{ cookiecutter.embedding_provider }}** 作为嵌入引擎。

```bash
 # 摄取本地文件（递归）
 {{ cookiecutter.project_slug }} rag-ingest /path/to/docs/ --collection documents --recursive

{%- if cookiecutter.enable_google_drive_ingestion %}
 # 从 Google Drive 拉取（服务账号认证）
 {{ cookiecutter.project_slug }} rag-sync-gdrive --collection documents --folder-id <id>
{%- endif %}
{%- if cookiecutter.enable_s3_ingestion %}
 # 从 S3 / MinIO 拉取
 {{ cookiecutter.project_slug }} rag-sync-s3 --collection documents --prefix docs/
{%- endif %}

 # 语义搜索
 {{ cookiecutter.project_slug }} rag-search "your query" --collection documents
```

 PDF 解析使用 **{{ cookiecutter.pdf_parser }}**。查看 `docs/howto/add-rag-source.md` 了解如何添加新的源连接器。
{%- endif %}
{%- if cookiecutter.use_frontend %}

---

 ## 前端

```bash
cd frontend
bun install
bun dev          # http://localhost:{{ cookiecutter.frontend_port }}
bun run lint
bun run build
```

 前端通过 `src/app/api/*` 中的 Next.js API 路由处理器与后端通信（服务端代理，将认证 Cookie 转发给 FastAPI 后端）。有意避免从浏览器直接调用 `localhost:{{ cookiecutter.backend_port }}`。

 i18n（PL + EN）通过 `next-intl` 开箱即用。通过扩展 `messages/<lang>.json` 和 `src/i18n.ts` 添加新语言。
{%- endif %}

---

 ## 部署

 ### 前端 → Vercel

```bash
cd frontend && npx vercel --prod
```

 在 Vercel 控制面板中设置：

- `BACKEND_URL` = `https://api.your-domain.com`
- `BACKEND_WS_URL` = `wss://api.your-domain.com`
- `NEXT_PUBLIC_AUTH_ENABLED` = `true`
{%- if cookiecutter.enable_rag %}
- `NEXT_PUBLIC_RAG_ENABLED` = `true`
{%- endif %}

 ### 后端 → 你的服务器

```bash
 # 1. SSH 到服务器，克隆仓库
 # 2. cp backend/.env.example backend/.env，填写真实的密钥
 # 3. 参考 nginx/nginx.conf 配置 Nginx
 # 4. 启动服务栈：
 make prod
 
 # 日常操作：
 make prod-logs
 make prod-down
```

 迁移在 `make prod` 时自动运行。在新主机上首次部署时，同样使用 `make prod` 作为自举命令。

---

 ## 指南
 
 | 指南 | 说明 |
 |-------|-------|
 | `docs/howto/add-api-endpoint.md` | 添加新的 REST 端点 |
 | `docs/howto/add-agent-tool.md` | 创建 Agent 工具 |
 | `docs/howto/customize-agent-prompt.md` | 调整系统提示词 |
{%- if cookiecutter.background_tasks != "none" %}
 | `docs/howto/add-background-task.md` | 添加后台任务 |
{%- endif %}
{%- if cookiecutter.enable_rag %}
 | `docs/howto/add-rag-source.md` | 添加 RAG 文档源 |
 | `docs/howto/add-sync-connector.md` | 构建自定义同步连接器 |
{%- endif %}

---

 *由 [全栈 AI Agent 模板](https://github.com/vstorm-co/framework-agent-python) v{{ cookiecutter.generator_version }} 生成。*
