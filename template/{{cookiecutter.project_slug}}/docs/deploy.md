# 部署

本项目使用以下与部署相关的标志生成：

{% if cookiecutter.enable_docker %}- ✅ Docker / `docker-compose.yml`{% else %}- ❌ 无 Docker（手动部署）{% endif %}
{% if cookiecutter.enable_kubernetes %}- ✅ Kubernetes 清单文件在 `k8s/`{% else %}- ❌ 无 Kubernetes 清单文件{% endif %}
- CI: `{{ cookiecutter.ci_type }}`
{% if cookiecutter.use_nginx %}- 反向代理：Nginx{% endif %}
{% if cookiecutter.use_traefik %}- 反向代理：Traefik{% endif %}

---

{% if cookiecutter.enable_docker %}
## Docker Compose（单主机）

用于预发布环境或小型生产环境：

```bash
# 1. 配置
cp backend/.env.example backend/.env
# Edit backend/.env with production values (see ENV_VARS.md)

# 2. 构建 + 启动
docker compose up -d --build

# 3. 应用迁移
docker compose exec app uv run alembic upgrade head


# 4. 验证
curl http://localhost:{{ cookiecutter.backend_port }}/api/v1/health
{% if cookiecutter.use_frontend %}# 前端：http://localhost:{{ cookiecutter.frontend_port }}{% endif %}
```

### 反向代理

{%- if cookiecutter.use_nginx %}
Nginx 配置在 `nginx/` 中，将 `/` 代理到前端，`/api` 代理到后端，`/ws` 代理到后端 WebSocket。在 `nginx/conf.d/app.conf` 中更新 `server_name` 和 TLS 证书路径。
{%- elif cookiecutter.use_traefik %}
`docker-compose.yml` 中的 Traefik 标签基于 `Host()` 进行路由。设置 `DOMAIN` 环境变量，然后将 DNS 指向主机。通过标签配置 ACME / Let's Encrypt——取消 `docker-compose.yml` 中的注释并设置 `ACME_EMAIL`。
{%- else %}
使用你自己的反向代理（Caddy / Nginx / ALB）。后端监听 `:{{ cookiecutter.backend_port }}`，前端监听 `:{{ cookiecutter.frontend_port }}`。
{%- endif %}
{% endif %}

{% if cookiecutter.enable_kubernetes %}

## Kubernetes

`k8s/` 中的清单文件涵盖：Deployment、Service、ConfigMap、Secret 存根、Ingress、可选的 HPA。

```bash
# 构建 + 推送镜像
docker build -t your-registry/{{ cookiecutter.project_slug }}-backend:latest backend/
{% if cookiecutter.use_frontend %}docker build -t your-registry/{{ cookiecutter.project_slug }}-frontend:latest frontend/
{% endif %}docker push your-registry/{{ cookiecutter.project_slug }}-backend:latest

# Update image tags in k8s/deployment.yaml, then:
kubectl create namespace {{ cookiecutter.project_slug }}
kubectl -n {{ cookiecutter.project_slug }} create secret generic app-secrets --from-env-file=backend/.env
kubectl apply -n {{ cookiecutter.project_slug }} -f k8s/

# 迁移作为 Job 运行
kubectl -n {{ cookiecutter.project_slug }} apply -f k8s/migration-job.yaml
```

### 调优

- **副本数：** 编辑 `k8s/deployment.yaml`。后端是异步的——从 2 个副本开始。
- **HPA：** 如果存在 `k8s/hpa.yaml`，基于 CPU 自动扩缩。调整阈值。
- **资源：** 请求/限制已保守设置。如果处理大文件{% if cookiecutter.enable_rag %} 或有大量并发 RAG 查询{% endif %}，增加内存。
{% endif %}

## 各平台快速开始

### Fly.io

```bash
fly launch --name {{ cookiecutter.project_slug }}-backend --region waw
{% if cookiecutter.use_postgresql %}fly postgres create --name {{ cookiecutter.project_slug }}-db
fly postgres attach {{ cookiecutter.project_slug }}-db
{% endif %}{% if cookiecutter.enable_redis %}# Redis：使用 Upstash（`fly redis create`）或 Fly's Tigris{% endif %}
fly secrets set $(cat backend/.env | grep -v '^#' | xargs)
fly deploy
```

### Railway

1. 连接仓库，选择基于 Dockerfile 的部署。
2. 将 `backend/.env` 中的环境变量添加到 Railway 服务。
{% if cookiecutter.use_postgresql %}3. 配置 PostgreSQL 插件 → `DATABASE_URL` 自动注入。
{% endif %}{% if cookiecutter.enable_redis %}4. 配置 Redis 插件 → `REDIS_URL` 自动注入。
{% endif %}5. 部署。

### Render

1. 创建 Web Service → docker，指向 `backend/Dockerfile`。
{% if cookiecutter.use_frontend %}2. 为前端创建静态站点（构建命令：`bun install && bun run build`，输出目录：`.next`）。
{% endif %}{% if cookiecutter.use_postgresql %}3. 创建 PostgreSQL → 复制 DATABASE_URL。
{% endif %}4. 添加环境变量；部署。

### Vercel（仅前端）
{% if cookiecutter.use_frontend %}
前端是 Next.js 应用——在 Vercel 上开箱即用。

```bash
cd frontend
vercel
```

在 Vercel 控制面板中设置 `BACKEND_URL` 和 `NEXT_PUBLIC_API_URL` 环境变量，指向你的后端主机。
{% else %}
不适用——本项目未生成前端。
{% endif %}

---

## 生产环境验证

在升级到生产环境前，运行：

```bash
docker compose exec app uv run python -c "from app.core.config import settings; print('OK')"
```

提前发现缺失的必需环境变量。参见 `ENV_VARS.md` 获取完整列表。

## 部署后检查清单

- [ ] `/api/v1/health` 返回 `{"status": "ok"}`
- [ ] `alembic current` 匹配预期的版本
{% if cookiecutter.use_frontend %}- [ ] 前端正常渲染，登录流程端到端可用
{% endif %}{% if cookiecutter.enable_billing %}- [ ] Stripe 测试 Webhook 正常投递（使用 Stripe CLI：`stripe listen --forward-to https://your-domain/api/v1/billing/webhook`）
{% endif %}{% if cookiecutter.enable_email %}- [ ] 测试邮件发送（触发密码重置流程）
{% endif %}- [ ] 日志正常流向汇聚工具{% if cookiecutter.enable_sentry %} + Sentry 捕获错误{% endif %}{% if cookiecutter.enable_logfire %} + Logfire 接收追踪数据{% endif %}
- [ ] 反向代理强制执行 HTTPS

## 回滚

- **模式：** `alembic downgrade -1` 回滚一个迁移。先在预发布环境测试。
- **代码：** 重新部署之前的镜像标签。固定标签（`v1.2.3`），绝不要将 `latest` 部署到生产环境。
- **数据：** 从最近的备份恢复；确认 `alembic current` 与数据版本匹配。
