 # {{ cookiecutter.project_name }} 的手动设置步骤
 
 生成器创建了代码。以下是**无法自动化的一次性外部设置步骤**——
 需要创建的账户、需要复制的密钥、需要配置的服务。
 
 > 跳到末尾的"每次部署后"部分，查看需要定期重复执行的事项。以上项目是每个环境一次性的。
 
 ---
 
 ## 密钥
 
 ```bash
 cp backend/.env.example backend/.env
 ```
 
 然后在 `backend/.env` 中：
 
 - [ ] **`SECRET_KEY`** — 替换为新值：`openssl rand -hex 32`
 - [ ] **`API_KEY`** — 替换为新值：`openssl rand -hex 32`
 
 这些用于签名 JWT 和认证服务间调用。每次环境升级时轮换（dev → staging → prod 各使用自己的密钥）。
 
 ## PostgreSQL
 
 - [ ] 配置 PostgreSQL ≥ 14 实例（本地：`docker compose up -d db`；托管：Neon / Supabase / RDS / Cloud SQL）。
 - [ ] 在 `.env` 中将 `DATABASE_URL` 设置为**异步**连接字符串：`postgresql+asyncpg://user:pass@host:5432/dbname`。
 - [ ] 运行迁移：`cd backend && uv run alembic upgrade head`。

{%- if cookiecutter.use_openai %}

 ## OpenAI
 
 - [ ] 在 https://platform.openai.com/api-keys 创建 API 密钥。
 - [ ] 在 `.env` 中设置 `OPENAI_API_KEY`。
 - [ ]（可选）在 OpenAI 控制面板设置消费限额，避免意外账单。
{%- endif %}

{%- if cookiecutter.use_anthropic %}

 ## Anthropic
 
 - [ ] 在 https://console.anthropic.com/ 创建 API 密钥。
 - [ ] 在 `.env` 中设置 `ANTHROPIC_API_KEY`。
{%- endif %}

{%- if cookiecutter.use_google %}

 ## Google AI Studio
 
 - [ ] 在 https://aistudio.google.com/ 创建 API 密钥。
 - [ ] 在 `.env` 中设置 `GOOGLE_API_KEY`。
{%- endif %}

{%- if cookiecutter.use_openrouter %}

 ## OpenRouter
 
 - [ ] 在 https://openrouter.ai/keys 创建 API 密钥。
 - [ ] 在 `.env` 中设置 `OPENROUTER_API_KEY`。
{%- endif %}

{%- if cookiecutter.enable_oauth_google %}

 ## Google OAuth
 
 - [ ] 前往 https://console.cloud.google.com/ → API 和服务 → 凭据 → 创建 OAuth 客户端 ID。
 - [ ] 应用类型：**Web 应用**。
 - [ ] 授权重定向 URI：`{{ cookiecutter.frontend_port and "http://localhost:" + cookiecutter.frontend_port|string or "http://localhost:3000" }}/auth/callback`。部署时添加生产环境 URL。
 - [ ] 复制**客户端 ID** + **客户端密钥** → 在 `.env` 中设置 `GOOGLE_OAUTH_CLIENT_ID` + `GOOGLE_OAUTH_CLIENT_SECRET`。
{%- endif %}

{%- if cookiecutter.enable_rag %}

 ## RAG（{{ cookiecutter.vector_store }}）
{% if cookiecutter.use_milvus %}
 - [ ] 本地：`docker compose up -d milvus etcd minio`（已包含在 `docker-compose.yml` 中）。
 - [ ] 云端：通过 Zilliz Cloud 配置，设置 `MILVUS_URI` + `MILVUS_TOKEN`。
{%- elif cookiecutter.use_qdrant %}
 - [ ] 本地：`docker compose up -d qdrant`。
 - [ ] 云端：配置 Qdrant Cloud，设置 `QDRANT_URL` + `QDRANT_API_KEY`。
{%- elif cookiecutter.use_chromadb %}
 - [ ] 本地：`docker compose up -d chroma`（或运行嵌入式模式——设置 `CHROMA_HOST=localhost`）。
 - [ ] Chroma 没有托管云服务；生产环境建议使用 Milvus 或 Qdrant。
{%- elif cookiecutter.use_pgvector %}
 - [ ] 针对你的 PostgreSQL 数据库运行 `CREATE EXTENSION vector;`（已添加到迁移 `0007` 中）。
{%- endif %}

 - [ ]（可选）摄取种子文档：`uv run {{ cookiecutter.project_slug }} rag-ingest /path/to/file.pdf --collection docs`。
{%- if cookiecutter.enable_google_drive_ingestion %}

 ### Google Drive 同步源

 - [ ] 在 https://console.cloud.google.com/iam-admin/serviceaccounts 创建服务账号。
 - [ ] 下载 JSON 凭据 → 保存到 `secrets/gdrive-service-account.json`。
 - [ ] 将目标 Drive 文件夹共享给服务账号邮箱。
 - [ ] 在 `.env` 中设置 `GOOGLE_DRIVE_CREDENTIALS_FILE`。
{%- endif %}
{%- if cookiecutter.enable_s3_ingestion %}

 ### S3 / MinIO 同步源

 - [ ] 配置 S3 Bucket（或本地运行 MinIO：`docker compose up -d minio`）。
 - [ ] 创建 IAM 用户，对源 Bucket 授予 `s3:GetObject` + `s3:ListBucket` 权限。
 - [ ] 在 `.env` 中设置 `S3_ACCESS_KEY` / `S3_SECRET_KEY` / `RAG_S3_BUCKET` / `RAG_S3_PREFIX`。
{%- endif %}
{%- endif %}

{%- if cookiecutter.enable_redis %}

 ## Redis
 
 - [ ] 本地：`docker compose up -d redis`（已包含在 Compose 文件中）。
 - [ ] 托管：Upstash / Redis Cloud / ElastiCache。在 `.env` 中设置 `REDIS_URL`。
{%- endif %}

{%- if cookiecutter.enable_billing %}

 ## Stripe 计费
 
 - [ ] 在 https://dashboard.stripe.com/ 创建账户。
 - [ ] 获取 API 密钥（开发者 → API 密钥）：在 `.env` 中设置 `STRIPE_SECRET_KEY` + `STRIPE_PUBLISHABLE_KEY`。
 - [ ] 在 Stripe 控制面板创建产品 + 价格，然后将 ID 同步到种子迁移或 `plans` 表。
 - [ ] 设置 Webhook 端点：
   - 端点 URL：`https://your-backend/api/v1/billing/webhook`
   - 事件：`checkout.session.completed`、`customer.subscription.{created,updated,deleted}`、`invoice.{paid,payment_failed}`、`payment_intent.succeeded`
   - 复制签名密钥 → 在 `.env` 中设置 `STRIPE_WEBHOOK_SECRET`。
 - [ ] 通过 Stripe CLI 测试：`stripe listen --forward-to localhost:{{ cookiecutter.backend_port }}/api/v1/billing/webhook`。
{%- endif %}

{%- if cookiecutter.enable_email %}

 ## 事务性邮件
{% if cookiecutter.email_provider == "resend" %}
 - [ ] 在 https://resend.com 注册。
 - [ ] 验证你的发送域名（DNS DKIM/SPF 记录）。
 - [ ] 创建 API 密钥 → 在 `.env` 中设置 `RESEND_API_KEY`。
 - [ ] 设置 `EMAIL_FROM=noreply@yourdomain.com`（必须在已验证域名上）。
{%- elif cookiecutter.email_provider == "smtp" %}
 - [ ] 选择提供商（SendGrid / Mailgun / Postmark / SES）。设置所需的 DNS 记录。
 - [ ] 创建 SMTP 凭据 → 在 `.env` 中设置 `SMTP_HOST` / `SMTP_PORT` / `SMTP_USERNAME` / `SMTP_PASSWORD`。
 - [ ] 设置 `EMAIL_FROM=noreply@yourdomain.com`。
{%- else %}
 - [ ] 无外部提供商——邮件写入标准输出（`log` 提供者）。仅用于开发。
 - [ ] 为 staging/prod 切换到 `resend` 或 `smtp`。
{%- endif %}
{%- endif %}

{%- if cookiecutter.enable_sentry %}

 ## Sentry
 
 - [ ] 在 https://sentry.io/ 创建项目。
 - [ ] 复制 DSN → 在 `.env` 中设置 `SENTRY_DSN`。
 - [ ]（可选）在 CI 中配置发布跟踪，部署前将 `SENTRY_RELEASE` 设置为 Git SHA。
{%- endif %}

{%- if cookiecutter.enable_logfire %}

 ## Logfire（Pydantic 可观测性）
 
 - [ ] 在 https://logfire.pydantic.dev 创建账户。
 - [ ] 本地运行一次 `uv run logfire auth` 以初始化。
 - [ ] 获取写入令牌 → 在非本地环境的 `.env` 中设置 `LOGFIRE_TOKEN`。
{%- endif %}

{%- if cookiecutter.enable_langsmith %}

 ## LangSmith
 
 - [ ] 在 https://smith.langchain.com 创建账户。
 - [ ] 获取 API 密钥 → 在 `.env` 中设置 `LANGSMITH_API_KEY` + `LANGSMITH_PROJECT={{ cookiecutter.project_slug }}`。
{%- endif %}

{%- if cookiecutter.enable_kubernetes %}

 ## Kubernetes 部署
 
 - [ ] 构建 + 推送镜像：参见 `docs/deploy.md` → Kubernetes 部分。
 - [ ] 从 `.env` 创建集群密钥：`kubectl create secret generic app-secrets --from-env-file=backend/.env`。
 - [ ] 更新 `k8s/deployment.yaml` 中的镜像标签。
 - [ ] 应用：`kubectl apply -f k8s/`。
{%- endif %}

---

 ## 每次部署后
 
 - [ ] 运行数据库迁移：`alembic upgrade head`（CI 步骤或部署后任务）。
 - [ ] 冒烟测试 `/api/v1/health` 返回 `{"status": "ok"}`。
 {% if cookiecutter.use_frontend %}- [ ] 前端加载正常，登录 → 仪表盘流程可用。
 {% endif %}{% if cookiecutter.enable_billing %}- [ ] Stripe Webhook 正常投递（查看 Stripe 控制面板 → 开发者 → Webhooks → 近期投递）。
 {% endif %}- [ ] 日志正常流向汇聚工具。

---

 ## 更多参考
 
 - `ENV_VARS.md` — 详尽的环境变量参考
 - `docs/deploy.md` — 各平台部署方案
 - `SECURITY.md` — 安全模型 + 生产环境加固检查清单
 - `CONTRIBUTING.md` — 开发环境搭建
 - `docs/architecture.md` — 代码库分层架构规则
