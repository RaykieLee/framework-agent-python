 # CLAUDE.md
 
 ## 项目概览
 
 **{{ cookiecutter.project_name }}** - 由 [全栈 AI Agent 模板](https://github.com/vstorm-co/framework-agent-python) 生成的 FastAPI 应用。
 
 **技术栈：** FastAPI + Pydantic v2
 {%- if True %}, PostgreSQL（asyncpg 异步）{%- endif %}
 {%- if False %}, MongoDB（Motor 异步）{%- endif %}
 {%- if False %}, SQLite（同步）{%- endif %}
 , JWT + API 密钥认证
 {%- if cookiecutter.enable_redis %}, Redis{%- endif %}
 {%- if cookiecutter.use_pydantic_ai %}, PydanticAI{%- endif %}
 {%- if cookiecutter.use_langchain %}, LangChain{%- endif %}
 {%- if cookiecutter.use_langgraph %}, LangGraph{%- endif %}{%- if cookiecutter.use_deepagents %}, DeepAgents{%- endif %}
 {%- if cookiecutter.enable_rag %}, RAG（{{ cookiecutter.vector_store }}）{%- endif %}
 {%- if cookiecutter.use_celery %}, Celery{%- endif %}
 {%- if cookiecutter.use_taskiq %}, Taskiq{%- endif %}
 {%- if cookiecutter.use_frontend %}, Next.js 15（i18n）{%- endif %}

## Commands

```bash
# Backend
cd backend
uv run uvicorn app.main:app --reload --port {{ cookiecutter.backend_port }}
uv run pytest
uv run pytest tests/test_file.py::test_name -v
uv run ruff check . --fix && uv run ruff format .
uv run ty check

# Database migrations
uv run alembic upgrade head
uv run alembic revision --autogenerate -m "Description"
{%- if cookiecutter.use_frontend %}

# Frontend
cd frontend
bun dev
bun test
bun run lint
{%- endif %}
{%- if cookiecutter.enable_docker %}

# Docker
docker compose up -d
{%- endif %}
{%- if cookiecutter.enable_rag %}

# RAG
uv run {{ cookiecutter.project_slug }} rag-collections
uv run {{ cookiecutter.project_slug }} rag-ingest /path/to/file.pdf --collection docs
uv run {{ cookiecutter.project_slug }} rag-search "query" --collection docs
{%- if cookiecutter.enable_google_drive_ingestion %}
uv run {{ cookiecutter.project_slug }} rag-sync-gdrive --collection docs
{%- endif %}
{%- if cookiecutter.enable_s3_ingestion %}
uv run {{ cookiecutter.project_slug }} rag-sync-s3 --collection docs
{%- endif %}

# Sync Sources
uv run {{ cookiecutter.project_slug }} cmd rag-sources
uv run {{ cookiecutter.project_slug }} cmd rag-source-add
uv run {{ cookiecutter.project_slug }} cmd rag-source-sync
{%- endif %}
```

 ## 硬边界
 
 以下是不易察觉但容易违反的规则，涉及面广，需要提前说明：
 
 - 仓库层使用 `db.flush()` + `db.refresh()`，**绝不能**使用 `db.commit()`——会话通过 `get_db_session` 自动提交。
 - 路由层仅调用服务层——**绝不能**直接导入或调用仓库层。
 - 路由处理器返回 `-> Any`；序列化由 `response_model` 处理（避免重复的 Pydantic 验证）。
 - 使用 `datetime.now(UTC)`，绝不使用 `datetime.utcnow()`。
 - API 密钥比较使用 `secrets.compare_digest()`，绝不使用 `==`。

 ## 详细约定

Path-scoped guidance lives in `.claude/rules/*` and loads automatically when you edit matching files — it is intentionally NOT repeated here:

- `architecture.md` — Routes → Services → Repositories, dependency injection, thin vs. thick domains
- `schemas-models.md` — Pydantic v2 schemas (`*Create`/`*Update`/`*Read`/`*List`), SQLAlchemy models
- `api-conventions.md` — REST structure, status codes, response format, pagination, auth
- `exceptions-security.md` — domain exceptions (`NotFoundError`, etc.), JWT, RBAC
- `code-style.md` — formatting, naming, imports, type hints
- `testing.md` — test structure, fixtures, async patterns
{%- if cookiecutter.use_frontend %}
 - `frontend.md` — Next.js 15 约定
{%- endif %}

 长文档：`docs/architecture.md`、`docs/adding_features.md`、`docs/testing.md`、`docs/patterns.md`。
