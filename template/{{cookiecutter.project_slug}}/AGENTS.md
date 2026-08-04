 # AGENTS.md
 
 本文件为 AI 编码 Agent（Codex、Copilot、Cursor、Zed、OpenCode）提供指引。
 
 ## 项目概览
 
 **{{ cookiecutter.project_name }}** - 由 [全栈 AI Agent 模板](https://github.com/vstorm-co/framework-agent-python) 生成的 FastAPI 应用。
 
 **技术栈：** FastAPI + Pydantic v2
 {%- if True %}, PostgreSQL{%- endif %}
 , JWT + API 密钥认证
 {%- if cookiecutter.enable_redis %}, Redis{%- endif %}
 , {{ cookiecutter.ai_framework }}（{{ cookiecutter.llm_provider }}）
 {%- if cookiecutter.enable_rag %}, RAG（{{ cookiecutter.vector_store }}）{%- endif %}
 {%- if cookiecutter.use_frontend %}, Next.js 15（i18n）{%- endif %}
 
 ## 命令
 
 ```bash
 # 运行服务器
 cd backend && uv run uvicorn app.main:app --reload
 
 # 测试 & 代码检查
 pytest
 ruff check . --fix && ruff format .
 
 # 数据库迁移
 uv run alembic upgrade head
 uv run alembic revision --autogenerate -m "Description"
 {%- if cookiecutter.enable_rag %}
 
 # RAG
 uv run {{ cookiecutter.project_slug }} rag-ingest /path/to/file.pdf --collection docs
 uv run {{ cookiecutter.project_slug }} rag-search "query" --collection docs
 
 # 同步源
 uv run {{ cookiecutter.project_slug }} cmd rag-sources
 uv run {{ cookiecutter.project_slug }} cmd rag-source-add
 uv run {{ cookiecutter.project_slug }} cmd rag-source-sync
 {%- endif %}
 ```
 
 ## 项目结构
 
 ```
 backend/app/
 ├── api/routes/v1/    # 端点
 ├── services/         # 业务逻辑
 ├── repositories/     # 数据访问
 ├── schemas/          # Pydantic 模型
 ├── db/models/        # 数据库模型
 ├── agents/           # AI Agent
 {%- if cookiecutter.enable_rag %}
 ├── rag/              # RAG（嵌入、向量存储、摄取）
 │   └── connectors/   # 同步源连接器
 {%- endif %}
 └── commands/         # CLI 命令
 ```
 
 ## 关键约定
 
 - 仓库层使用 `db.flush()`，而非 `commit()`
 - 服务层抛出 `NotFoundError`、`AlreadyExistsError` 等异常
 - 分离的 `Create`、`Update`、`Response` 模式
 - 命令从 `app/commands/` 自动发现
 {%- if cookiecutter.enable_rag %}
 - 通过 CLI 和 API 上传进行文档摄取
 - 同步源：可配置的连接器，支持定时同步
 {%- endif %}
 
 ## 更多信息
 
 - `docs/architecture.md` - 架构详情
 - `docs/adding_features.md` - 如何添加功能
 - `docs/testing.md` - 测试指南
 - `docs/patterns.md` - 代码模式
