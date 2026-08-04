 # 配置参考
 
 所有配置通过环境变量管理，从 `backend/.env` 加载，
 使用 [pydantic-settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)。
 
 设置在 `app/core/config.py` 中定义，通过全局 `settings` 对象访问：
 
 ```python
 from app.core.config import settings
 
 print(settings.AI_MODEL)
 print(settings.DEBUG)
 ```
 
 ## 快速开始

```bash
cd backend

 # 复制示例文件（如果使用 --generate-env 生成则可能已存在）
 cp .env.example .env
 
 # 生成安全的密钥
 openssl rand -hex 32
 # 将输出粘贴到 .env 中的 SECRET_KEY
```

 ## 项目设置
 
 | 变量 | 默认值 | 说明 |
 |----------|---------|-------------|
 | `PROJECT_NAME` | `{{ cookiecutter.project_name }}` | 项目显示名称 |
 | `API_V1_STR` | `/api/v1` | API 版本前缀 |
 | `DEBUG` | `false` | 启用调试模式（详细错误、自动重载） |
 | `ENVIRONMENT` | `local` | 可选值：`development`、`local`、`staging`、`production` |
 | `TIMEZONE` | `{{ cookiecutter.timezone }}` | IANA 时区（例如 `UTC`、`Europe/Warsaw`、`America/New_York`） |
 | `MODELS_CACHE_DIR` | `./models_cache` | 缓存 ML 模型的目录 |
 | `MEDIA_DIR` | `./media` | 上传文件目录 |
 | `MAX_UPLOAD_SIZE_MB` | `50` | 最大文件上传大小（MB） |

{%- if cookiecutter.use_jwt %}

 ## 认证
 
 ### JWT
 
 | 变量 | 默认值 | 说明 |
 |----------|---------|-------------|
 | `SECRET_KEY` |（不安全的默认值）| JWT 签名密钥。生产环境中**必须**更改。生成方式：`openssl rand -hex 32` |
 | `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | 访问令牌有效期 |
 | `REFRESH_TOKEN_EXPIRE_MINUTES` | `10080` | 刷新令牌有效期（7 天） |
 | `ALGORITHM` | `HS256` | JWT 签名算法 |
 
 生产环境验证：`SECRET_KEY` 必须至少 32 个字符，且在 `ENVIRONMENT=production` 时不能使用默认值。
{%- endif %}

{%- if cookiecutter.use_api_key %}

 ### API 密钥
 
 | 变量 | 默认值 | 说明 |
 |----------|---------|-------------|
 | `API_KEY` | `change-me-in-production` | 用于程序化访问的共享 API 密钥 |
 | `API_KEY_HEADER` | `X-API-Key` | API 密钥的 HTTP 头名称 |
 
 生产环境验证：`ENVIRONMENT=production` 时，`API_KEY` 不能使用默认值。
{%- endif %}

{%- if cookiecutter.enable_oauth_google %}

 ### OAuth2（Google）
 
 | 变量 | 默认值 | 说明 |
 |----------|---------|-------------|
 | `GOOGLE_CLIENT_ID` |（空）| Google OAuth2 客户端 ID |
 | `GOOGLE_CLIENT_SECRET` |（空）| Google OAuth2 客户端密钥 |
 | `GOOGLE_REDIRECT_URI` | `http://localhost:{{ cookiecutter.backend_port }}/api/v1/oauth/google/callback` | OAuth2 回调 URL |
 | `FRONTEND_URL` | `http://localhost:{{ cookiecutter.frontend_port }}` | 用于 OAuth2 重定向的前端 URL |
{%- endif %}


 ## 数据库（PostgreSQL）
 
 | 变量 | 默认值 | 说明 |
 |----------|---------|-------------|
 | `POSTGRES_HOST` | `localhost` | PostgreSQL 主机 |
 | `POSTGRES_PORT` | `5432` | PostgreSQL 端口 |
 | `POSTGRES_USER` | `postgres` | PostgreSQL 用户 |
 | `POSTGRES_PASSWORD` |（空）| PostgreSQL 密码 |
 | `POSTGRES_DB` | `{{ cookiecutter.project_slug }}` | 数据库名称 |
 | `DB_POOL_SIZE` | `{{ cookiecutter.db_pool_size }}` | 连接池大小 |
 | `DB_MAX_OVERFLOW` | `{{ cookiecutter.db_max_overflow }}` | 最大溢出连接数 |
 | `DB_POOL_TIMEOUT` | `{{ cookiecutter.db_pool_timeout }}` | 连接池超时（秒） |
 
 计算属性：
 - `DATABASE_URL` — 异步连接字符串（`postgresql+asyncpg://...`）
 - `DATABASE_URL_SYNC` — 供 Alembic 使用的同步连接字符串



{%- if cookiecutter.enable_redis %}

 ## Redis
 
 | 变量 | 默认值 | 说明 |
 |----------|---------|-------------|
 | `REDIS_HOST` | `localhost` | Redis 主机 |
 | `REDIS_PORT` | `6379` | Redis 端口 |
 | `REDIS_PASSWORD` |（无）| Redis 密码（可选）|
 | `REDIS_DB` | `0` | Redis 数据库编号 |
{%- endif %}

 ## AI Agent
 
 | 变量 | 默认值 | 说明 |
 |----------|---------|-------------|
{%- if cookiecutter.use_openai %}
 | `OPENAI_API_KEY` |（空）| OpenAI API 密钥 |
 | `AI_MODEL` | `gpt-5.5` | 聊天使用的默认 LLM 模型 |
{%- endif %}
{%- if cookiecutter.use_anthropic %}
 | `ANTHROPIC_API_KEY` |（空）| Anthropic API 密钥 |
 | `AI_MODEL` | `claude-opus-4-7` | 聊天使用的默认 LLM 模型 |
{%- endif %}
{%- if cookiecutter.use_google %}
 | `GOOGLE_API_KEY` |（空）| Google AI API 密钥 |
 | `AI_MODEL` | `gemini-2.5-flash` | 聊天使用的默认 LLM 模型 |
{%- endif %}
{%- if cookiecutter.use_openrouter %}
 | `OPENROUTER_API_KEY` |（空）| OpenRouter API 密钥 |
 | `AI_MODEL` | `anthropic/claude-opus-4-7` | 聊天使用的默认 LLM 模型 |
{%- endif %}
 | `AI_TEMPERATURE` | `0.7` | LLM 温度（0.0 = 确定性，1.0 = 创造性）|
 | `AI_AVAILABLE_MODELS` |（自动配置）| UI 模型选择器中显示的模型 JSON 列表 |
 | `AI_FRAMEWORK` | `{{ cookiecutter.ai_framework }}` | AI 框架（信息性）|
 | `LLM_PROVIDER` | `{{ cookiecutter.llm_provider }}` | LLM 提供商（信息性）|

 ### 自定义可用模型
 
 覆盖 `.env` 中的 `AI_AVAILABLE_MODELS` 以自定义模型选择器：

```bash
AI_AVAILABLE_MODELS=["gpt-5.5","gpt-5.4","claude-opus-4-7"]
```

{%- if cookiecutter.enable_logfire %}

## Observability (Logfire)

| Variable | Default | Description |
|----------|---------|-------------|
 | `LOGFIRE_TOKEN` |（无）| Pydantic Logfire 令牌。在 https://logfire.pydantic.dev 获取 |
 | `LOGFIRE_SERVICE_NAME` | `{{ cookiecutter.project_slug }}` | Logfire 仪表盘中的服务名称 |
 | `LOGFIRE_ENVIRONMENT` | `development` | 环境标签 |
{%- endif %}

{%- if cookiecutter.enable_langsmith %}

## Observability (LangSmith)

| Variable | Default | Description |
|----------|---------|-------------|
 | `LANGCHAIN_TRACING_V2` | `true` | 启用 LangSmith 追踪 |
 | `LANGCHAIN_API_KEY` |（无）| LangSmith API 密钥。在 https://smith.langchain.com 获取 |
 | `LANGCHAIN_PROJECT` | `{{ cookiecutter.project_slug }}` | LangSmith 中的项目名称 |
 | `LANGCHAIN_ENDPOINT` | `https://api.smith.langchain.com` | LangSmith API 端点 |
{%- endif %}

{%- if cookiecutter.enable_web_search %}

## Web Search

| Variable | Default | Description |
|----------|---------|-------------|
 | `TAVILY_API_KEY` |（空）| 用于网页搜索工具的 Tavily API 密钥。在 https://tavily.com 获取 |
{%- endif %}

{%- if cookiecutter.use_deepagents %}

 ## DeepAgents
 
 | 变量 | 默认值 | 说明 |
 |----------|---------|-------------|
 | `DEEPAGENTS_BACKEND_TYPE` | `state` | 后端：`state`（内存中、临时）|
 | `DEEPAGENTS_MEMORY_PATHS` |（无）| Agent 启动时加载的逗号分隔的 AGENTS.md 记忆文件路径 |
 | `DEEPAGENTS_SKILLS_PATHS` |（无）| 逗号分隔的技能目录路径 |
 | `DEEPAGENTS_ENABLE_FILESYSTEM` | `true` | 启用文件系统工具（ls、read、write、edit、glob、grep）|
 | `DEEPAGENTS_ENABLE_EXECUTE` | `false` | 启用 Shell 执行（出于安全默认禁用）|
 | `DEEPAGENTS_ENABLE_TODOS` | `true` | 启用 write_todos 工具 |
 | `DEEPAGENTS_ENABLE_SUBAGENTS` | `true` | 启用生成子 Agent 的任务工具 |
 | `DEEPAGENTS_INTERRUPT_TOOLS` |（无）| 需要人工批准的工具（逗号分隔，或 `"all"`）|
 | `DEEPAGENTS_ALLOWED_DECISIONS` | `approve,edit,reject` | 中断工具的允许决策 |
{%- endif %}

{%- if cookiecutter.enable_rag %}

 ## RAG（检索增强生成）
 
 ### 向量数据库

{%- if cookiecutter.use_milvus %}

| Variable | Default | Description |
|----------|---------|-------------|
 | `MILVUS_HOST` | `localhost` | Milvus 主机 |
 | `MILVUS_PORT` | `19530` | Milvus 端口 |
 | `MILVUS_DATABASE` | `default` | Milvus 数据库名称 |
 | `MILVUS_TOKEN` | `root:Milvus` | Milvus 认证令牌 |
{%- endif %}

{%- if cookiecutter.use_qdrant %}

| Variable | Default | Description |
|----------|---------|-------------|
 | `QDRANT_HOST` | `localhost` | Qdrant 主机 |
 | `QDRANT_PORT` | `6333` | Qdrant 端口 |
 | `QDRANT_API_KEY` |（空）| Qdrant API 密钥（可选）|
{%- endif %}

{%- if cookiecutter.use_chromadb %}

| Variable | Default | Description |
|----------|---------|-------------|
 | `CHROMA_HOST` |（空）| ChromaDB 主机。留空使用嵌入式/持久化模式。|
 | `CHROMA_PORT` | `8100` | ChromaDB 端口（使用客户端-服务器模式时）|
 | `CHROMA_PERSIST_DIR` | `./chroma_data` | 嵌入式模式的数据目录 |
{%- endif %}

{%- if cookiecutter.use_pgvector %}

 pgvector 使用现有的 PostgreSQL 连接。无需额外配置。
{%- endif %}

 ### 嵌入
 
 | 变量 | 默认值 | 说明 |
 |----------|---------|-------------|
{%- if cookiecutter.use_openai_embeddings %}
 | `EMBEDDING_MODEL` | `text-embedding-3-small` | OpenAI 嵌入模型 |
{%- elif cookiecutter.use_voyage_embeddings %}
 | `EMBEDDING_MODEL` | `voyage-3` | Voyage AI 嵌入模型 |
 | `VOYAGE_API_KEY` |（空）| Voyage AI API 密钥 |
{%- elif cookiecutter.use_gemini_embeddings %}
 | `EMBEDDING_MODEL` | `gemini-embedding-exp-03-07` | Google Gemini 嵌入模型 |
{%- elif cookiecutter.use_sentence_transformers %}
 | `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Sentence Transformers 模型（本地运行）|
{%- else %}
 | `EMBEDDING_MODEL` | `text-embedding-3-small` | 嵌入模型 |
{%- endif %}

 ### 分块与检索
 
 | 变量 | 默认值 | 说明 |
 |----------|---------|-------------|
 | `RAG_CHUNK_SIZE` | `512` | 每个块的最大字符数 |
 | `RAG_CHUNK_OVERLAP` | `50` | 块之间的重叠字符数 |
 | `RAG_CHUNKING_STRATEGY` | `recursive` | 分块策略：`recursive`、`markdown`、`fixed` |
 | `RAG_DEFAULT_COLLECTION` | `documents` | 搜索默认集合（由 Agent 工具使用）|
 | `RAG_TOP_K` | `10` | 返回结果的默认数量 |
 | `RAG_HYBRID_SEARCH` | `false` | 启用 BM25 + 向量混合搜索 |
 | `RAG_ENABLE_OCR` | `false` | 扫描 PDF 的 OCR 回退（需要 `tesseract-ocr`）|

### Document Parsing

{%- if cookiecutter.use_all_pdf_parsers %}

| Variable | Default | Description |
|----------|---------|-------------|
 | `PDF_PARSER` | `pymupdf` | RAG 摄取的 PDF 解析器：`pymupdf`、`llamaparse`、`liteparse` |
 | `CHAT_PDF_PARSER` | `pymupdf` | 聊天文件上传的 PDF 解析器：`pymupdf`、`llamaparse`、`liteparse` |
 | `LLAMAPARSE_API_KEY` |（空）| LlamaParse API 密钥（`llamaparse` 解析器必需）|
 | `LLAMAPARSE_TIER` | `agentic` | LlamaParse 层级：`fast`、`cost_effective`、`agentic`、`agentic_plus` |
{%- elif cookiecutter.use_llamaparse %}

| Variable | Default | Description |
|----------|---------|-------------|
 | `LLAMAPARSE_API_KEY` |（空）| LlamaParse API 密钥 |
 | `LLAMAPARSE_TIER` | `agentic` | LlamaParse 层级：`fast`、`cost_effective`、`agentic`、`agentic_plus` |
{%- endif %}

{%- if cookiecutter.enable_reranker %}

### Reranking

{%- if cookiecutter.use_cohere_reranker %}

| Variable | Default | Description |
|----------|---------|-------------|
 | `COHERE_API_KEY` |（空）| 用于重排的 Cohere API 密钥 |
{%- endif %}

{%- if cookiecutter.use_cross_encoder_reranker %}

| Variable | Default | Description |
|----------|---------|-------------|
 | `HF_TOKEN` |（空）| HuggingFace 令牌（用于受限模型）|
 | `CROSS_ENCODER_MODEL` | `cross-encoder/ms-marco-MiniLM-L6-v2` | 用于重排的交叉编码器模型 |
{%- endif %}
{%- endif %}

{%- if cookiecutter.enable_rag_image_description %}

### Image Description

| Variable | Default | Description |
|----------|---------|-------------|
 | `RAG_IMAGE_DESCRIPTION_MODEL` |（空，使用 `AI_MODEL`）| 用于描述文档中图片的 LLM 模型 |
{%- endif %}

{%- if cookiecutter.enable_google_drive_ingestion %}

### Google Drive Sync

| Variable | Default | Description |
|----------|---------|-------------|
 | `GOOGLE_DRIVE_CREDENTIALS_FILE` | `credentials/google-drive-sa.json` | Google 服务账号凭据文件路径 |
{%- endif %}

{%- if cookiecutter.enable_s3_ingestion %}

### S3/MinIO Sync

| Variable | Default | Description |
|----------|---------|-------------|
 | `S3_RAG_ENDPOINT` |（无）| S3/MinIO 端点 URL |
 | `S3_RAG_ACCESS_KEY` |（空）| 访问密钥 |
 | `S3_RAG_SECRET_KEY` |（空）| 秘密密钥 |
 | `S3_RAG_BUCKET` | `{{ cookiecutter.project_slug }}-rag` | Bucket 名称 |
 | `S3_RAG_REGION` | `us-east-1` | AWS 区域 |
{%- endif %}
{%- endif %}

{%- if cookiecutter.use_telegram or cookiecutter.use_slack %}

 ## 消息渠道
 
 | 变量 | 默认值 | 说明 |
 |----------|---------|-------------|
 | `CHANNEL_ENCRYPTION_KEY` |（空）| 用于加密机器人令牌和同步源连接器凭据的 Fernet 密钥。生成方式：`python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` |
{%- if cookiecutter.use_telegram %}
 | `TELEGRAM_WEBHOOK_BASE_URL` |（空）| Telegram Webhook 的基础 URL（例如 `https://yourdomain.com`）。仅在 Webhook 模式下需要 |
{%- endif %}
{%- if cookiecutter.use_slack %}
 | `SLACK_SIGNING_SECRET` |（空）| Slack 应用签名密钥，用于 Events API 签名验证 |
 | `SLACK_BOT_TOKEN` |（空）| Slack 机器人 OAuth 令牌（`xoxb-...`），用于通过 Web API 发送消息 |
 | `SLACK_APP_TOKEN` |（空）| Slack 应用级令牌（`xapp-...`），用于 Socket 模式（仅开发）|
{%- endif %}

{%- endif %}

{%- if cookiecutter.use_celery %}

 ## Celery
 
 | 变量 | 默认值 | 说明 |
 |----------|---------|-------------|
 | `CELERY_BROKER_URL` | `redis://localhost:6379/0` | Celery 消息代理 URL |
 | `CELERY_RESULT_BACKEND` | `redis://localhost:6379/0` | Celery 结果后端 URL |
{%- endif %}

{%- if cookiecutter.use_taskiq %}

 ## Taskiq
 
 | 变量 | 默认值 | 说明 |
 |----------|---------|-------------|
 | `TASKIQ_BROKER_URL` | `redis://localhost:6379/1` | Taskiq 消息代理 URL |
 | `TASKIQ_RESULT_BACKEND` | `redis://localhost:6379/1` | Taskiq 结果后端 URL |
{%- endif %}

{%- if cookiecutter.use_arq %}

 ## ARQ（异步 Redis 队列）
 
 | 变量 | 默认值 | 说明 |
 |----------|---------|-------------|
 | `ARQ_REDIS_HOST` | `localhost` | ARQ 的 Redis 主机 |
 | `ARQ_REDIS_PORT` | `6379` | ARQ 的 Redis 端口 |
 | `ARQ_REDIS_PASSWORD` |（无）| ARQ 的 Redis 密码 |
 | `ARQ_REDIS_DB` | `2` | ARQ 的 Redis 数据库编号 |
{%- endif %}

{%- if cookiecutter.enable_cors %}

 ## CORS
 
 | 变量 | 默认值 | 说明 |
 |----------|---------|-------------|
 | `CORS_ORIGINS` | `["http://localhost:3000","http://localhost:8080"]` | 允许的来源（JSON 数组）|
 | `CORS_ALLOW_CREDENTIALS` | `true` | 允许凭据（Cookie）|
 | `CORS_ALLOW_METHODS` | `["*"]` | 允许的 HTTP 方法 |
 | `CORS_ALLOW_HEADERS` | `["*"]` | 允许的 HTTP 头 |
 
 生产环境验证：`ENVIRONMENT=production` 时，`CORS_ORIGINS` 不能包含 `"*"`。
{%- endif %}

{%- if cookiecutter.enable_rate_limiting %}

 ## 限流
 
 | 变量 | 默认值 | 说明 |
 |----------|---------|-------------|
 | `RATE_LIMIT_REQUESTS` | `{{ cookiecutter.rate_limit_requests }}` | 每周期最大请求数 |
 | `RATE_LIMIT_PERIOD` | `{{ cookiecutter.rate_limit_period }}` | 周期（秒）|
{%- endif %}

{%- if cookiecutter.enable_sentry %}

## Sentry

| Variable | Default | Description |
|----------|---------|-------------|
 | `SENTRY_DSN` |（无）| 用于错误追踪的 Sentry DSN |
{%- endif %}

{%- if cookiecutter.enable_prometheus %}

## Prometheus

| Variable | Default | Description |
|----------|---------|-------------|
 | `PROMETHEUS_METRICS_PATH` | `/metrics` | 指标端点路径 |
 | `PROMETHEUS_INCLUDE_IN_SCHEMA` | `false` | 在 OpenAPI 模式中包含指标端点 |
{%- endif %}

{%- if cookiecutter.enable_file_storage %}

 ## 文件存储（S3/MinIO）
 
 | 变量 | 默认值 | 说明 |
 |----------|---------|-------------|
 | `S3_ENDPOINT` |（无）| S3/MinIO 端点 URL |
 | `S3_ACCESS_KEY` |（空）| 访问密钥 |
 | `S3_SECRET_KEY` |（空）| 秘密密钥 |
 | `S3_BUCKET` | `{{ cookiecutter.project_slug }}` | Bucket 名称 |
 | `S3_REGION` | `us-east-1` | AWS 区域 |
{%- endif %}

{%- if cookiecutter.enable_docker %}

 ## Docker / 生产环境
 
 | 变量 | 默认值 | 说明 |
 |----------|---------|-------------|
 | `DOMAIN` | `example.com` | 生产环境域名（用于 Traefik）|
 | `ACME_EMAIL` | `admin@example.com` | Let's Encrypt 用于 SSL 证书的邮箱 |
{%- if cookiecutter.enable_redis %}
 | `REDIS_PASSWORD` | `change-me-in-production` | 生产环境的 Redis 密码 |
{%- endif %}
{%- if cookiecutter.use_celery %}
 | `FLOWER_USER` | `admin` | Flower 监控 UI 用户名 |
 | `FLOWER_PASSWORD` | `change-me-in-production` | Flower 监控 UI 密码 |
{%- endif %}
{%- endif %}

 ## 生产环境检查清单
 
 部署到生产环境前，确保以下变量已正确设置：

{%- if cookiecutter.use_jwt %}
 1. `SECRET_KEY` — 生成唯一的 64 字符十六进制密钥：`openssl rand -hex 32`
{%- endif %}
{%- if cookiecutter.use_api_key %}
 2. `API_KEY` — 生成唯一密钥：`openssl rand -hex 32`
{%- endif %}
 3. `ENVIRONMENT` — 设置为 `production`
 4. `DEBUG` — 设置为 `false`
 5. `POSTGRES_PASSWORD` — 使用强唯一密码
{%- if cookiecutter.enable_cors %}
 6. `CORS_ORIGINS` — 仅列出你实际的前端域名
{%- endif %}
{%- if cookiecutter.enable_redis %}
 7. `REDIS_PASSWORD` — 设置强密码
{%- endif %}
{%- if cookiecutter.use_openai %}
 8. `OPENAI_API_KEY` — 你的生产环境 API 密钥
{%- endif %}
{%- if cookiecutter.use_anthropic %}
 8. `ANTHROPIC_API_KEY` — 你的生产环境 API 密钥
{%- endif %}
{%- if cookiecutter.use_google %}
 8. `GOOGLE_API_KEY` — 你的生产环境 API 密钥
{%- endif %}
{%- if cookiecutter.use_openrouter %}
 8. `OPENROUTER_API_KEY` — 你的生产环境 API 密钥
{%- endif %}
