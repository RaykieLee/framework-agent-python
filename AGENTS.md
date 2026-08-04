# AGENTS.md

AI 编码助手（Codex、Copilot、Cursor、Zed、OpenCode）在此仓库中工作的指导说明。

## 项目概述

**全栈 AI 代理模板** — CLI 工具，用于生成生产就绪的 FastAPI + Next.js 项目，支持 AI 代理（5 个框架）、RAG（4 个向量数据库）和 20+ 企业级集成。

## 命令

```bash
uv sync                    # 安装依赖
uv run pytest              # 运行测试
uv run ruff check . --fix  # 代码检查
uv run ruff format .       # 格式化
uv run mypy fastapi_gen    # 类型检查
```

## CLI

```bash
framework-agent-python                                  # 交互式向导（默认）
framework-agent-python create my_app --database postgresql
framework-agent-python create my_app --rag --task-queue celery
framework-agent-python templates                        # 列出所有选项
```

生成的项目 CLI 包含同步源命令：
```bash
uv run <project_slug> cmd rag-sources              # 列出已配置的源
uv run <project_slug> cmd rag-source-add           # 添加新源
uv run <project_slug> cmd rag-source-sync          # 触发源同步
```

## 架构

| 模块 | 用途 |
|--------|---------|
| `fastapi_gen/cli.py` | Click CLI：`new`、`create`、`templates` |
| `fastapi_gen/config.py` | Pydantic 模型、枚举、验证、cookiecutter 上下文 |
| `fastapi_gen/prompts.py` | 交互式提示（Questionary） |
| `fastapi_gen/generator.py` | Cookiecutter 调用 |

### 模板（`template/`）

```
template/
├── cookiecutter.json            # ~120 个变量
├── hooks/post_gen_project.py    # 清理与格式化
└── {{cookiecutter.project_slug}}/
    ├── backend/app/             # FastAPI（代理、RAG、服务、仓库）
    └── frontend/                # Next.js 15（可选）
```

Jinja2 条件语句：`{%- if cookiecutter.enable_rag %}...{%- endif %}`

## 主要功能

- **6 个 AI 框架**：PydanticAI、PydanticDeep、LangChain、LangGraph、DeepAgents、AgentScope
- **4 个 LLM 提供商**：OpenAI、Anthropic、Google Gemini、OpenRouter
- **RAG**：4 个向量数据库（Milvus、Qdrant、ChromaDB、pgvector）、4 个嵌入提供商、重排序、图像描述
- **文档源**：本地文件（CLI）、API 上传、Google Drive（服务账号）、S3/MinIO
- **同步源**：可配置的连接器（Google Drive、S3），支持定时同步
- **PDF 解析器**：PyMuPDF、LiteParse、LlamaParse（通过环境变量运行时选择）
- **可观测性**：Logfire（PydanticAI）、LangSmith（LangChain/LangGraph/DeepAgents）

## 常见任务

**添加新的 CLI 选项：**
1. 添加到 `config.py`（`ProjectConfig` 或其子模型的枚举/字段）
2. 添加提示到 `prompts.py`
3. 添加到 `cookiecutter.json`
4. 在模板文件中添加条件语句
5. 更新 `hooks/post_gen_project.py` 进行清理
6. 在 `template/VARIABLES.md` 中记录

**添加新的向量数据库：**
1. 添加到 `config.py` 的 `VectorStoreType` 枚举
2. 添加 `use_<name>` 到 `to_cookiecutter_context()`
3. 在 `rag/vectorstore.py` 中实现 `<Name>VectorStore(BaseVectorStore)`
4. 在 `api/deps.py`、`commands/rag.py`、`agents/tools/rag_tool.py` 中添加条件
5. 添加 Docker 服务（如需要）和依赖

**添加新的同步连接器：**
1. 在 `rag/connectors/` 中创建连接器类，遵循 `BaseConnector` 模式
2. 在 `rag/connectors/__init__.py` 中注册连接器类型
3. 在 `commands/rag.py` 中添加 CLI 命令（例如 `rag-source-add`、`rag-source-sync`）
4. 在 `schemas/sync_source.py` 中添加同步源 schema
5. 在 `worker/tasks/rag_tasks.py` 中接入后台任务

## 参考

| 资源 | 位置 |
|----------|----------|
| 模板变量 | `template/cookiecutter.json` |
| 变量文档 | `template/VARIABLES.md` |
| 生成后钩子 | `template/hooks/post_gen_project.py` |
| CLI 帮助 | `framework-agent-python templates` |
