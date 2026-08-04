 # 安全
 
 ## 报告漏洞
 
 邮箱：**{{ cookiecutter.author_email }}**（或在仓库上打开私有安全公告）。请包含：
 
 - 受影响的版本 / 提交
 - 复现步骤
 - 影响评估（数据泄露 / 权限提升 / 拒绝服务等）
 
 我们承诺在 48 小时内确认，高严重性问题在 7 天内发布修复。

---

 ## 安全模型

 ### 认证

{%- if cookiecutter.use_jwt %}
 - **JWT（`HS256`）** 使用 `SECRET_KEY` 签名。访问令牌 TTL = `ACCESS_TOKEN_EXPIRE_MINUTES`（默认 30 分钟）。刷新令牌 TTL = `REFRESH_TOKEN_EXPIRE_MINUTES`（默认 7 天）。
 - **密码哈希：** 通过 `passlib` 使用 bcrypt。明文密码绝不持久化。
{%- if cookiecutter.enable_oauth_google %}
 - **OAuth 2.0（Google）** — 授权码流程。服务端验证令牌，通过邮箱查找/创建内部用户记录。
{%- endif %}
{%- if cookiecutter.enable_session_management %}
 - **会话管理** — 基于数据库的会话，支持撤销。每次颁发刷新令牌时创建会话记录；`/sessions` 端点允许用户查看 + 撤销设备。
{%- else %}
 - **无状态 JWT** — 无数据库会话表。登出在客户端进行（丢弃令牌）。如需服务端撤销，请使用 `--session-management` 重新生成。
{%- endif %}
{%- endif %}
{%- if cookiecutter.use_api_key %}
 - **管理 API 密钥** — 静态 `settings.API_KEY`，通过 `X-API-Key` 头匹配，用于服务间调用。使用 `secrets.compare_digest()` 进行常量时间比较。
{%- endif %}

 ### 授权

 - **基于角色** 通过 `RoleChecker` 依赖实现（`UserRole.USER` / `UserRole.ADMIN`）。
{%- if cookiecutter.enable_admin_panel %}
 - **管理页面** 需要 `role=admin`。敏感操作（模拟用户、系统健康检查）单独控制。
{%- endif %}
{%- if cookiecutter.enable_teams %}
 - **工作空间范围** — 每个经过认证的请求解析一个 `ActiveOrg`（默认 = 个人组织）。资源通过 `organization_id` 外键限定范围。
 - **组织角色：** `OWNER` / `ADMIN` / `MEMBER`。所有者可以转移所有权 + 删除组织。
{%- endif %}

 ### 传输 / 网络

 - **CORS** — 来源列表来自 `settings.CORS_ORIGINS`。生产环境中限制为你自己的域名。
 - **HTTPS** — 通过反向代理（Nginx / Traefik / ALB）强制执行。当 `ENVIRONMENT=production` 时，中间件设置 Strict-Transport-Security 头。
 - **CSP** — 前端默认设置 `frame-ancestors 'none'` 以防止点击劫持。{% if cookiecutter.use_frontend %} 参见 `frontend/next.config.ts` 的 headers 块。{% endif %}

 ### 数据

 - **密钥** — 通过 `pydantic-settings` 从环境变量读取。永不提交到代码仓库。参见 `.env.example` 和 `ENV_VARS.md`。
{%- if cookiecutter.enable_admin_features_audit_log %}
 - **审计日志** — 管理员变更操作（用户更新、删除、模拟、角色更改）记录到 `app_admin_audit_log` 表中，包含操作者、IP 和负载快照。
{%- endif %}
{%- if cookiecutter.enable_billing %}
 - **Stripe Webhook** — 通过 `stripe.Webhook.construct_event(secret=STRIPE_WEBHOOK_SECRET)` 验证签名。幂等表防止重放。
{%- endif %}
{%- if cookiecutter.enable_rag %}
 - **RAG 文档** — 文件上传按组织限定范围。没有公开的读取端点；所有检索在聊天期间在服务端进行。
{%- endif %}

 ### 生产环境加固检查清单

 - [ ] 轮换 `SECRET_KEY` 和 `API_KEY`，不要使用生成的默认值。
 - [ ] 设置 `DEBUG=false` 和 `ENVIRONMENT=production`。
 - [ ] 将 `CORS_ORIGINS` 限制为你的域名。
{%- if cookiecutter.enable_rate_limiting %}
 - [ ] 在 `.env` 中调整 `RATE_LIMIT_REQUESTS` / `RATE_LIMIT_PERIOD`。
{%- endif %}
{%- if cookiecutter.enable_prometheus %}
 - [ ] 如果 `/metrics` 暴露在公共端点上，设置 `PROMETHEUS_AUTH_TOKEN`。
{%- endif %}
{%- if cookiecutter.enable_sentry %}
 - [ ] 设置 `SENTRY_DSN` 以发送错误。确认 `core/sentry.py` 中的 PII 清除规则。
{%- endif %}
 - [ ] 在代理层强制执行 HTTPS。
 - [ ] 在 CI 中运行 `pip-audit` / `bun audit` 检查依赖漏洞。
 - [ ] 配置数据库备份 + 恢复测试计划。
{%- if cookiecutter.enable_billing %}
 - [ ] 订阅 Stripe Webhook 到所有相关事件；通过 Stripe CLI 验证端点。
{%- endif %}

 ## 已知限制

 - **开箱即用不支持 2FA / MFA**。计划通过 `pyotp` 添加 TOTP——参见 `notes/thingstofix.md` §A.13。
 - **除 Google OAuth 外，不支持 SAML / OIDC**。企业 SSO 需要自定义 IdP 集成。
 - **日志中没有自动 PII 编辑**——注意记录的内容。
{%- if cookiecutter.use_jwt and not cookiecutter.enable_session_management %}
 - **不支持服务端会话撤销**——JWT 在过期前一直有效。令牌泄露需要轮换 `SECRET_KEY`（会使所有会话失效）。启用 `--session-management` 进行选择性撤销。
{%- endif %}
