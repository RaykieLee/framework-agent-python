 # 架构指南
 
 本项目遵循**仓库层 + 服务层**的分层架构。
 每个功能——用户、对话、文件、RAG 文档、同步源——都使用
 相同的模式：**模型 → 模式 → 仓库 → 服务 → 端点**。
 
 ## 请求流程
 
 ```
 HTTP 请求 → API 路由 → 服务层 → 仓库层 → 数据库
                    ↓
              响应 ← 服务层 ← 仓库层 ←
 ```
 
 路由层绝不包含直接数据库调用。所有数据访问都经过
 服务层，再由服务层委托给仓库层。
 
 ## 目录结构（`backend/app/`）

 | 目录 / 文件 | 用途 |
 |-----------|---------|
 | `api/routes/v1/` | HTTP 端点、请求验证、认证 |
 | `api/deps.py` | 依赖注入（数据库会话、当前用户） |
 | **`services/`** | **业务逻辑、编排** |
 | ↳ `user.py` | 用户 CRUD、个人资料更新 |
 | ↳ `conversation.py` | 对话与消息管理 |
 | ↳ `message_rating.py` | 消息评分 CRUD、统计、导出 |
 | ↳ `file_upload.py` | 聊天文件上传处理 |
 | ↳ `file_storage.py` | 文件存储抽象（本地 / S3） |
{%- if cookiecutter.enable_rag %}
 | ↳ `rag_document.py` | RAG 文档生命周期 |
 | ↳ `rag_sync.py` | 远程源同步编排 |
 | ↳ `sync_source.py` | 同步源 CRUD |
{%- endif %}
 | **`repositories/`** | **数据访问层、数据库查询** |
 | ↳ `user.py` | 用户查询 |
 | ↳ `conversation.py` | 对话查询 |
 | ↳ `chat_file.py` | 聊天文件查询 |
 | ↳ `message_rating.py` | 消息评分查询 |
{%- if cookiecutter.enable_rag %}
 | ↳ `rag_document.py` | RAG 文档查询 |
 | ↳ `sync_log.py` | 同步日志查询 |
 | ↳ `sync_source.py` | 同步源查询 |
{%- endif %}
 | **`schemas/`** | **Pydantic 请求/响应模型** |
 | ↳ `user.py` | 用户模式 |
 | ↳ `conversation.py` | 对话与消息模式 |
 | ↳ `file.py` | 文件上传模式 |
 | ↳ `message_rating.py` | 消息评分模式 |
{%- if cookiecutter.enable_rag %}
 | ↳ `rag.py` | RAG 查询/响应模式 |
 | ↳ `sync_source.py` | 同步源模式 |
{%- endif %}
 | **`db/models/`** | **SQLAlchemy 2.0 模型** |
 | ↳ `user.py` | 用户模型 |
 | ↳ `conversation.py` | 对话与消息模型 |
 | ↳ `chat_file.py` | 聊天文件模型 |
 | ↳ `message_rating.py` | 消息评分模型 |
 | ↳ `webhook.py` | Webhook 模型 |
{%- if cookiecutter.enable_rag %}
 | ↳ `rag_document.py` | RAG 文档模型 |
 | ↳ `sync_log.py` | 同步日志模型 |
 | ↳ `sync_source.py` | 同步源模型 |
{%- endif %}
 | `core/config.py` | 通过 pydantic-settings 配置 |
 | `core/security.py` | JWT / API 密钥工具 |
 | `agents/` | AI Agent 和工具 |
{%- if cookiecutter.enable_rag %}
 | `rag/` | RAG 模块（嵌入、向量存储、检索） |
 | `rag/connectors/` | 同步连接器（Google Drive、S3） |
{%- endif %}
 | `commands/` | Django 风格的 CLI 命令 |
{%- if cookiecutter.use_celery or cookiecutter.use_taskiq %}
 | `worker/` | 后台任务定义 |
{%- endif %}

 ## 各层职责

 ### API 路由层（`api/routes/v1/`）
 - HTTP 请求/响应处理
 - 通过 Pydantic 模式进行输入验证
 - 认证和授权检查
 - **绝不**包含直接数据库调用——始终委托给服务层

 ### 服务层（`services/`）
 - 业务逻辑和验证
 - 编排一个或多个仓库调用
 - 抛出领域异常（`NotFoundError`、`AlreadyExistsError` 等）
 - 管理事务边界

 ### 仓库层（`repositories/`）
 - 仅数据库操作
 - 无业务逻辑
 - 使用 `db.flush()` 而非 `commit()`（依赖注入的会话管理事务）
 - 返回领域模型

 ### 模式层（`schemas/`）
 - 每个实体分离 `Create`、`Update` 和 `Response` 模型
 - `Response` 模式使用 `model_config = ConfigDict(from_attributes=True)` 进行 ORM 转换

 ### 模型层（`db/models/`）
 - SQLAlchemy 2.0 模型定义
 - 关系、索引和列默认值在此定义
{%- if cookiecutter.enable_rag %}

 ### RAG 连接器（`rag/connectors/`）
 - 可插拔的同步适配器，实现 `BaseSyncConnector`
 - 每个连接器提供 `list_files()` 和 `download_file()`
 - 在 `CONNECTOR_REGISTRY` 中注册，以便运行时发现
{%- endif %}

 ## 关键文件
 
 - 入口点：`app/main.py`
 - 配置：`app/core/config.py`
 - 依赖：`app/api/deps.py`
 - 认证工具：`app/core/security.py`
 - 异常处理器：`app/api/exception_handlers.py`

{%- if cookiecutter.use_jwt %}

 ## 认证与授权
 
 ### 认证方式
 
 项目支持两种认证方式，均始终可用：
 
 1. **JWT（JSON Web 令牌）**—— 由前端和 API 客户端使用。
    - 通过 `POST /api/v1/auth/login` 登录，返回 `access_token` + `refresh_token`。
    - 访问令牌在 `ACCESS_TOKEN_EXPIRE_MINUTES` 后过期（默认 30 分钟）。
    - 刷新令牌在 `REFRESH_TOKEN_EXPIRE_MINUTES` 后过期（默认 7 天）。
    - 前端将令牌存储为 HTTP-only Cookie。
    - WebSocket 认证通过查询参数（`?token=<jwt>`）或 Cookie 传递 JWT。
{%- if cookiecutter.use_api_key %}

 2. **API 密钥**—— 用于服务器间和程序化访问。
    - 通过 `X-API-Key` 头传递（可通过 `API_KEY_HEADER` 配置）。
    - 通过 `API_KEY` 环境变量设置的单个共享密钥。
    - 使用常量时间比较（`secrets.compare_digest`）防止时序攻击。
{%- endif %}

 ### 角色
 
 在 `UserRole` 中定义了两个角色（参见 `app/db/models/user.py`）：
 
 | 角色 | 值 | 说明 |
 |------|-------|-------------|
 | **ADMIN** | `"admin"` | 完全系统访问权限，可管理用户、RAG、Webhook、导出 |
 | **USER** | `"user"` | 标准访问权限：聊天、个人资料、搜索 |
 
 角色层级：`ADMIN` 拥有所有访问权限。如果用户是管理员，`User` 模型上的 `has_role()` 方法对任何角色返回 `True`。

 ### RoleChecker 工作原理

 `RoleChecker` 是 `app/api/deps.py` 中一个可调用的 FastAPI 依赖类：

```python
class RoleChecker:
    def __init__(self, required_role: UserRole) -> None:
        self.required_role = required_role

    async def __call__(self, user: User = Depends(get_current_user)) -> User:
        if not user.has_role(self.required_role):
            raise AuthorizationError(...)
        return user
```

 在路由中使用：

```python
 # 任何已认证用户
 @router.get("/profile")
 async def profile(current_user: CurrentUser): ...

 # 仅管理员
 @router.get("/all-users")
 async def list_users(current_user: CurrentAdmin): ...
```

 类型别名如下：
 - `CurrentUser` = `Annotated[User, Depends(get_current_user)]`——任何已认证用户
 - `CurrentAdmin` = `Annotated[User, Depends(RoleChecker(UserRole.ADMIN))]`——需要管理员角色
 - `CurrentSuperuser` = `Annotated[User, Depends(get_current_active_superuser)]`——管理员的旧别名

 ### IDOR 防护
 
 对话和文件端点在服务层强制执行所有权检查：
 - 对话将 `user_id=current_user.id` 传递给服务层，服务层按所有者过滤查询。
 - 文件下载在返回文件前验证 `chat_file.user_id == current_user.id`。
 - 这防止了用户访问属于其他用户的资源。

 有关完整的端点级权限，请参见 `docs/permissions.md`。
{%- endif %}

 ## 聊天中的文件处理

{%- if cookiecutter.use_jwt %}

 当用户在聊天界面上传文件时，执行以下流水线：

```
Upload (POST /files/upload)
  -> Validate (MIME type + size)
  -> Classify (image / pdf / docx / text)
  -> Parse (extract text content)
  -> Store (save to media/{user_id}/)
  -> Record (create ChatFile in DB)
  -> Link (attach to message when sent)
```

 ### 支持的文件类型

| Category | Extensions | Processing |
|----------|-----------|------------|
 | 图片 | JPEG、PNG、WebP、GIF | 原样存储，以二进制形式发送给 LLM 进行视觉分析 |
 | PDF | .pdf | 通过配置的解析器提取文本 |
 | 文档 | .docx | 通过 python-docx 提取文本 |
 | 文本 | .txt、.md | 直接 UTF-8 解码 |

 ### 解析器选择

{%- if cookiecutter.use_all_pdf_parsers %}
 `CHAT_PDF_PARSER` 环境变量控制哪个解析器处理聊天文件上传中的 PDF。
 选项：`pymupdf`（默认、最快、本地）、`llamaparse`
（AI 驱动、需要 API 密钥）、`liteparse`。失败时回退到 `pymupdf`。
{%- else %}
 PDF 使用 PyMuPDF 解析（快速、本地、无需 API 密钥）。
{%- endif %}

 ### 存储

 文件通过 `FileStorageService` 保存到 `media/{user_id}/`。`ChatFile`
 模型存储 `storage_path`、`filename`、`mime_type`、`size`、`file_type`
 和 `parsed_content`（提取的文本）。只有文件所有者可以访问其文件。

 ### 大小限制
 
 最大上传大小由 `MAX_UPLOAD_SIZE_MB` 控制（默认 50MB）。
{%- endif %}

{%- if cookiecutter.enable_rag %}

 ## RAG 系统
 
 ### 架构概览
 
 RAG（检索增强生成）系统提供了一个知识库，AI Agent 可以在对话期间搜索。其组成如下：

```
Documents -> Parse -> Chunk -> Embed -> Vector Store
                                            |
User Query -> Embed -> Search -> Rerank? -> Results -> Agent Prompt
```

 ### 关键原则：RAG 是全局的

 **集合对所有用户共享。** 没有按用户的文档隔离。这意味着：
 
 - 任何已认证用户都可以**搜索**任何集合。
 - 只有**管理员**可以创建/删除集合、上传文档、配置同步源以及查看同步日志。
 - 知识库作为全组织范围的共享资源。

 ### 组件
 
 | 组件 | 文件 | 用途 |
 |-----------|------|---------|
 | `DocumentProcessor` | `rag/documents.py` | 将文件解析为文本（PDF、DOCX、TXT、图片） |
 | `IngestionService` | `rag/ingestion.py` | 编排解析 → 分块 → 嵌入 → 存储 |
 | `RetrievalService` | `rag/retrieval.py` | 处理带过滤和评分的搜索查询 |
 | `EmbeddingService` | `rag/embeddings.py` | 通过配置的提供商生成嵌入向量 |
 | `BaseVectorStore` | `rag/vectorstore.py` | 向量数据库操作的抽象接口 |
{%- if cookiecutter.use_milvus %}
 | `MilvusVectorStore` | `rag/vectorstore.py` | Milvus 实现 |
{%- elif cookiecutter.use_qdrant %}
 | `QdrantVectorStore` | `rag/vectorstore.py` | Qdrant 实现 |
{%- elif cookiecutter.use_chromadb %}
 | `ChromaVectorStore` | `rag/vectorstore.py` | ChromaDB 实现 |
{%- elif cookiecutter.use_pgvector %}
 | `PgVectorStore` | `rag/vectorstore.py` | pgvector（PostgreSQL）实现 |
{%- endif %}

 ### 摄取流水线
 
 文档可以通过以下方式摄取：
 
 1. **CLI** — `uv run {{ cookiecutter.project_slug }} cmd rag-ingest <path>`
 2. **API** — `POST /api/v1/rag/collections/{name}/ingest`（仅管理员，文件上传）
 3. **同步源** — 配置的连接器（Google Drive、S3）按计划或按需拉取文档

 每个摄取的文档会经历：
 - 解析为文本（由 `PDF_PARSER` 环境变量选择解析器）
 - 分割成块（可配置的 `RAG_CHUNK_SIZE` / `RAG_CHUNK_OVERLAP`）
 - 通过配置的嵌入提供商生成嵌入向量
 - 存储在向量数据库中
 - 通过 `RAGDocument` 模型在 SQL 中跟踪状态（`processing`、`done`、`error`）

 ### 同步模式
 
 | 模式 | 行为 |
 |------|----------|
 | `full` | 替换所有文档（重新摄取所有内容） |
 | `new_only` | 添加新文件，重新摄取内容哈希已更改的文件，跳过未更改的文件 |
 | `update_only` | 仅重新摄取已更改的文件，完全跳过新文件 |

 ### 同步连接器
 
 远程文档源使用 `rag/connectors/` 中的可插拔连接器。每个
 连接器实现 `BaseSyncConnector`，具有 `list_files()` 和 `download_file()`
 方法。参见 `docs/patterns.md` 了解如何添加新连接器。
{%- endif %}
