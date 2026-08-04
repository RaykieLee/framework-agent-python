 # 环境变量
 
 `{{ cookiecutter.project_name }}` 运行时配置参考。权威来源是
 `backend/.env.example`——本文档说明每组配置的用途以及哪些是必需的、哪些是可选的。
 
 > 快速开始：将 `backend/.env.example` 复制为 `backend/.env`，然后填写标记为 **必需** 的空白项。
 > 默认值适合本地开发。
 
 ## 项目
 
 | 变量 | 必需 | 默认值 | 说明 |
 |---|---|---|---|
 | `PROJECT_NAME` | 可选 | `{{ cookiecutter.project_name }}` | 用于日志、OpenAPI 标题、邮件模板 |
 | `DEBUG` | 可选 | `true` | 为 `true` 时，FastAPI 返回完整堆栈跟踪 |
 | `ENVIRONMENT` | 可选 | `local` | 自由格式标签：`local` / `staging` / `production` |
 | `TIMEZONE` | 可选 | `{{ cookiecutter.timezone }}` | IANA 时区名称（例如 `Europe/Warsaw`） |
 | `BACKEND_URL` | 可选 | `http://localhost:{{ cookiecutter.backend_port }}` | 前端 BFF + 邮件链接生成使用 |
 | `FRONTEND_URL` | 可选 | `http://localhost:{{ cookiecutter.frontend_port }}` | 密码重置 / 魔法链接邮件使用 |
 
 ## 认证与密钥
 
 | 变量 | 必需 | 默认值 | 说明 |
 |---|---|---|---|
 | `SECRET_KEY` | **生产环境必需** |（已生成）| JWT 签名密钥。轮换将使所有令牌失效 |
 | `API_KEY` | **生产环境必需** |（已生成）| 用于 `X-API-Key` 头的静态管理/服务间密钥 |
 | `ACCESS_TOKEN_EXPIRE_MINUTES` | 可选 | `30` | JWT 访问令牌有效期 |
 | `REFRESH_TOKEN_EXPIRE_MINUTES` | 可选 | `10080` | JWT 刷新令牌有效期（7 天） |
{%- if cookiecutter.enable_oauth_google %}
 | `GOOGLE_OAUTH_CLIENT_ID` | 必需 | — | 来自 Google Cloud Console → OAuth 凭据 |
 | `GOOGLE_OAUTH_CLIENT_SECRET` | 必需 | — | 来自 Google Cloud Console |
{%- endif %}

 ## 数据库
 | 变量 | 必需 | 默认值 | 说明 |
 |---|---|---|---|
 | `DATABASE_URL` | **必需** | `postgresql+asyncpg://...` | 完整异步连接字符串 |
 | `DB_POOL_SIZE` | 可选 | `{{ cookiecutter.db_pool_size }}` | 长连接数 |
 | `DB_MAX_OVERFLOW` | 可选 | `{{ cookiecutter.db_max_overflow }}` | 超出连接池大小的突发容量 |

 ## LLM / AI
{% if cookiecutter.use_openai %}
| Variable | Required | Default | Description |
|---|---|---|---|
 | `OPENAI_API_KEY` | **必需** | — | 来自 platform.openai.com |
 | `AI_MODEL` | 可选 | `gpt-5.5` | Agent 使用的默认模型（因提供商而异） |
{%- endif %}
{%- if cookiecutter.use_anthropic %}
 | `ANTHROPIC_API_KEY` | **必需** | — | 来自 console.anthropic.com |
{%- endif %}
{%- if cookiecutter.use_google %}
 | `GOOGLE_API_KEY` | **必需** | — | 来自 aistudio.google.com |
{%- endif %}
{%- if cookiecutter.use_openrouter %}
 | `OPENROUTER_API_KEY` | **必需** | — | 来自 openrouter.ai |
{%- endif %}
{%- if cookiecutter.enable_logfire %}
 | `LOGFIRE_TOKEN` | 可选 | — | 设置后，将追踪数据发送到 Logfire（logfire.pydantic.dev） |
{%- endif %}
{%- if cookiecutter.enable_langsmith %}
 | `LANGSMITH_API_KEY` | 可选 | — | 设置后，将追踪数据发送到 smith.langchain.com |
 | `LANGSMITH_PROJECT` | 可选 | `{{ cookiecutter.project_slug }}` | LangSmith 中的项目 Bucket |
{%- endif %}

{%- if cookiecutter.enable_rag %}

 ## RAG（{{ cookiecutter.vector_store }}）
 
 | 变量 | 必需 | 默认值 | 说明 |
 |---|---|---|---|
{%- if cookiecutter.use_milvus %}
 | `MILVUS_URI` | **必需** | `http://localhost:19530` | Milvus gRPC 端点 |
 | `MILVUS_TOKEN` | 可选 | — | 认证令牌（云端 Milvus） |
{%- elif cookiecutter.use_qdrant %}
 | `QDRANT_URL` | **必需** | `http://localhost:6333` | Qdrant REST 端点 |
 | `QDRANT_API_KEY` | 可选 | — | 认证（云端 Qdrant） |
{%- elif cookiecutter.use_chromadb %}
 | `CHROMA_HOST` | 可选 | `localhost` | Chroma 服务器主机 |
 | `CHROMA_PORT` | 可选 | `8000` | Chroma 服务器端口 |
{%- endif %}
{%- if cookiecutter.use_voyage_embeddings %}
 | `VOYAGE_API_KEY` | **必需** | — | 来自 voyageai.com |
{%- endif %}
{%- if cookiecutter.use_llamaparse %}
 | `LLAMA_CLOUD_API_KEY` | PDF 解析必需 | — | 来自 cloud.llamaindex.ai |
{%- endif %}
{%- if cookiecutter.enable_google_drive_ingestion %}
 | `GOOGLE_DRIVE_CREDENTIALS_FILE` | 必需 | — | 服务账号 JSON 文件路径 |
{%- endif %}
{%- if cookiecutter.enable_s3_ingestion %}
 | `RAG_S3_BUCKET` | 必需 | — | 用于摄取的源 Bucket |
 | `RAG_S3_PREFIX` | 可选 | `""` | 扫描的路径前缀 |
{%- endif %}
{%- endif %}

{%- if cookiecutter.enable_redis %}

 ## Redis
 
 | 变量 | 必需 | 默认值 | 说明 |
 |---|---|---|---|
 | `REDIS_URL` | **必需** | `redis://localhost:6379/0` | 用于{% if cookiecutter.enable_caching %} 缓存、{% endif %}{% if cookiecutter.use_celery %} Celery 消息代理、{% endif %}{% if cookiecutter.enable_rate_limiting %} 限流、{% endif %} 会话存储 |
{%- endif %}

{%- if cookiecutter.enable_email %}

 ## 邮件（{{ cookiecutter.email_provider }}）
 
 | 变量 | 必需 | 默认值 | 说明 |
 |---|---|---|---|
{%- if cookiecutter.email_provider == "resend" %}
 | `RESEND_API_KEY` | **必需** | — | 来自 resend.com |
 | `EMAIL_FROM` | **必需** | — | 已验证的发件人，例如 `noreply@yourdomain.com` |
{%- elif cookiecutter.email_provider == "smtp" %}
 | `SMTP_HOST` | **必需** | — | 例如 `smtp.sendgrid.net` |
 | `SMTP_PORT` | 可选 | `587` | TLS 端口 |
 | `SMTP_USERNAME` | **必需** | — | SMTP 认证用户 |
 | `SMTP_PASSWORD` | **必需** | — | SMTP 认证密码 |
 | `EMAIL_FROM` | **必需** | — | 已验证的发件人 |
{%- else %}
 |（日志提供者——无环境变量；邮件写入标准输出）| — | — | — |
{%- endif %}
{%- endif %}

{%- if cookiecutter.enable_billing %}

 ## Stripe 计费
 
 | 变量 | 必需 | 默认值 | 说明 |
 |---|---|---|---|
 | `STRIPE_SECRET_KEY` | **必需** | — | `sk_live_...`（或测试用 `sk_test_...`） |
 | `STRIPE_WEBHOOK_SECRET` | **必需** | — | 来自 Stripe 控制面板 Webhook 配置的 `whsec_...` |
 | `STRIPE_PUBLISHABLE_KEY` | **必需** | — | `pk_live_...` 暴露给前端 |
 | `BILLING_DEFAULT_CURRENCY` | 可选 | `{{ cookiecutter.billing_default_currency }}` | ISO-4217 货币代码 |
 | `BILLING_TRIAL_DAYS` | 可选 | `{{ cookiecutter.billing_trial_days_default }}` | 默认试用期长度 |
{%- if cookiecutter.enable_credits_system %}
 | `CREDITS_PER_USD` | 可选 | `{{ cookiecutter.billing_credits_per_usd }}` | 代币成本 → 积分的转化率 |
 | `CREDITS_LOW_THRESHOLD` | 可选 | `{{ cookiecutter.billing_credits_low_threshold }}` | 触发积分不足邮件的阈值 |
 | `CREDITS_FREE_TIER_GRANT` | 可选 | `{{ cookiecutter.billing_credits_free_tier_grant }}` | 新组织注册时赠送的积分 |
{%- endif %}
{%- endif %}

{%- if cookiecutter.enable_sentry %}

 ## Sentry
 
 | 变量 | 必需 | 默认值 | 说明 |
 |---|---|---|---|
 | `SENTRY_DSN` | 可选（为空则关闭） | — | 来自 sentry.io 项目设置 |
 | `SENTRY_ENVIRONMENT` | 可选 | `local` | 用于 `environment` 过滤器的标签 |
 | `SENTRY_TRACES_SAMPLE_RATE` | 可选 | `0.1` | 0.0–1.0 — 性能追踪采样率 |
{%- endif %}

{%- if cookiecutter.enable_prometheus %}

 ## Prometheus
 
 | 变量 | 必需 | 默认值 | 说明 |
 |---|---|---|---|
 | `PROMETHEUS_METRICS_PATH` | 可选 | `/metrics` | 暴露指标的 URL 路径 |
 | `PROMETHEUS_AUTH_TOKEN` | 可选（为空则关闭） | — | 设置后，`/metrics` 需要 `Authorization: Bearer <token>` |
{%- endif %}

{%- if cookiecutter.enable_file_storage %}

 ## 文件存储（S3/MinIO）
 
 | 变量 | 必需 | 默认值 | 说明 |
 |---|---|---|---|
 | `S3_ENDPOINT_URL` | 可选 |（AWS 默认值）| 为 MinIO/Backblaze 等设置 |
 | `S3_ACCESS_KEY` | **必需** | — | 访问密钥 ID |
 | `S3_SECRET_KEY` | **必需** | — | 秘密密钥 |
 | `S3_BUCKET` | **必需** | — | 默认上传 Bucket |
 | `S3_REGION` | 可选 | `us-east-1` | AWS 区域 |
{%- endif %}

 ## 验证

```bash
 # 确认设置加载无误：
 cd backend && uv run python -c "from app.core.config import settings; print(settings.model_dump_json(indent=2))"
```

 如果缺少任何**必需**变量，FastAPI 将在启动时抛出 `pydantic_settings.SettingsError`——查看错误消息以确定缺失的字段。
