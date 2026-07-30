# 部署指南

本指南介绍如何把生成的 FastAPI 项目部署到生产环境。

## 概览

生成的项目支持多种部署方式：

- **Docker Compose** —— 简单的单服务器部署
- **Kubernetes** —— 生产级编排
- **云平台** —— AWS、GCP、Azure 等

---

## 前置条件

部署前，请确保你具备：

1. 已在部署服务器上安装 **Docker**
2. 已配置**域名**(可选但推荐)
3. **SSL 证书**(推荐 Let's Encrypt)
4. 已为生产环境准备好**环境变量**

---

## 环境变量

### 生产环境必填

```bash
# Core
ENVIRONMENT=production
DEBUG=false

# Security - MUST be changed!
SECRET_KEY=your-secure-secret-key-at-least-32-characters
API_KEY=your-secure-api-key

# Database
POSTGRES_HOST=your-db-host
POSTGRES_PORT=5432
POSTGRES_USER=your-db-user
POSTGRES_PASSWORD=your-secure-db-password
POSTGRES_DB=your-db-name

# Redis (if enabled)
REDIS_HOST=your-redis-host
REDIS_PORT=6379
REDIS_PASSWORD=your-redis-password

# Logfire
LOGFIRE_TOKEN=your-logfire-token
LOGFIRE_ENVIRONMENT=production

# AI Agent (if enabled)
OPENAI_API_KEY=sk-your-key
```

### 生成安全密钥

```bash
# Generate SECRET_KEY
openssl rand -hex 32

# Generate API_KEY
openssl rand -hex 32

# Generate database password
openssl rand -base64 24
```

---

## Docker Compose 部署

### 生产配置

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    environment:
      - ENVIRONMENT=production
      - POSTGRES_HOST=db
      - POSTGRES_PORT=5432
      - POSTGRES_USER=${POSTGRES_USER}
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
      - POSTGRES_DB=${POSTGRES_DB}
      - SECRET_KEY=${SECRET_KEY}
      - LOGFIRE_TOKEN=${LOGFIRE_TOKEN}
    ports:
      - "8000:8000"
    depends_on:
      db:
        condition: service_healthy
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  db:
    image: postgres:16-alpine
    environment:
      - POSTGRES_USER=${POSTGRES_USER}
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
      - POSTGRES_DB=${POSTGRES_DB}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER}"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    command: redis-server --requirepass ${REDIS_PASSWORD}
    volumes:
      - redis_data:/data
    restart: unless-stopped

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    environment:
      - BACKEND_URL=http://backend:8000
    ports:
      - "3000:3000"
    depends_on:
      - backend
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
```

### 部署步骤

1. **克隆仓库**
   ```bash
   git clone https://github.com/your-org/your-project.git
   cd your-project
   ```

2. **配置 `backend/.env`**
   ```bash
   cp backend/.env.example backend/.env
   # Edit with real production values (the same file is used for dev and prod)
   ```

3. **构建并启动服务**
   ```bash
   make prod
   # equivalent to:
   # docker compose --env-file backend/.env -f docker-compose.prod.yml up -d --build
   ```

4. **执行数据库迁移**
   ```bash
   docker compose -f docker-compose.prod.yml exec backend alembic upgrade head
   ```

5. **创建管理员用户**
   ```bash
   docker compose -f docker-compose.prod.yml exec backend \
     python -m cli.commands user create-admin \
     --email admin@example.com
   ```

---

## Kubernetes 部署

### 前置条件

- Kubernetes 集群(GKE、EKS、AKS 或自管)
- 已配置 `kubectl`
- 容器仓库访问权限

### 清单文件

生成的项目在 `k8s/` 中包含 Kubernetes 清单：

```
k8s/
├── namespace.yaml
├── configmap.yaml
├── secret.yaml
├── backend/
│   ├── deployment.yaml
│   ├── service.yaml
│   └── hpa.yaml
├── frontend/
│   ├── deployment.yaml
│   └── service.yaml
├── database/
│   ├── statefulset.yaml
│   └── service.yaml
└── ingress.yaml
```

### 部署步骤

1. **创建命名空间**
   ```bash
   kubectl apply -f k8s/namespace.yaml
   ```

2. **创建 Secret**
   ```bash
   kubectl create secret generic app-secrets \
     --from-literal=secret-key=$(openssl rand -hex 32) \
     --from-literal=postgres-password=$(openssl rand -base64 24) \
     --from-literal=redis-password=$(openssl rand -base64 24) \
     -n your-namespace
   ```

3. **应用配置**
   ```bash
   kubectl apply -f k8s/configmap.yaml
   kubectl apply -f k8s/database/
   kubectl apply -f k8s/backend/
   kubectl apply -f k8s/frontend/
   kubectl apply -f k8s/ingress.yaml
   ```

4. **执行迁移**
   ```bash
   kubectl exec -it deploy/backend -n your-namespace -- alembic upgrade head
   ```

### 后端部署

```yaml
# k8s/backend/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend
  namespace: your-namespace
spec:
  replicas: 3
  selector:
    matchLabels:
      app: backend
  template:
    metadata:
      labels:
        app: backend
    spec:
      containers:
        - name: backend
          image: your-registry/backend:latest
          ports:
            - containerPort: 8000
          envFrom:
            - configMapRef:
                name: app-config
            - secretRef:
                name: app-secrets
          resources:
            requests:
              memory: "256Mi"
              cpu: "250m"
            limits:
              memory: "512Mi"
              cpu: "500m"
          livenessProbe:
            httpGet:
              path: /api/v1/health
              port: 8000
            initialDelaySeconds: 10
            periodSeconds: 30
          readinessProbe:
            httpGet:
              path: /api/v1/health/ready
              port: 8000
            initialDelaySeconds: 5
            periodSeconds: 10
```

### 水平 Pod 自动扩缩容

```yaml
# k8s/backend/hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: backend-hpa
  namespace: your-namespace
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: backend
  minReplicas: 2
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 80
```

---

## 反向代理(Nginx)

### 配置

```nginx
# /etc/nginx/sites-available/your-project
upstream backend {
    server 127.0.0.1:8000;
}

upstream frontend {
    server 127.0.0.1:3000;
}

server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

    # API routes
    location /api {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # WebSocket support
    location /api/v1/agent/ws {
        proxy_pass http://backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 86400;
    }

    # API docs
    location /docs {
        proxy_pass http://backend;
    }

    location /redoc {
        proxy_pass http://backend;
    }

    # Frontend
    location / {
        proxy_pass http://frontend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

## 数据库迁移

### 执行迁移

```bash
# Docker Compose
docker compose exec backend alembic upgrade head

# Kubernetes
kubectl exec -it deploy/backend -- alembic upgrade head

# Direct
cd backend && alembic upgrade head
```

### 创建迁移

```bash
# Generate migration
alembic revision --autogenerate -m "Add new table"

# Apply migration
alembic upgrade head

# Rollback
alembic downgrade -1
```

---

## 监控

### Logfire

应用已接入 Logfire,提供：

- **Trace** —— 请求流和延迟
- **日志** —— 结构化的应用日志
- **指标** —— 自定义指标和计数器

在 [logfire.pydantic.dev](https://logfire.pydantic.dev) 访问控制台。

### 健康检查

```bash
# Liveness (is the app running?)
curl https://your-domain.com/api/v1/health

# Readiness (is the app ready to serve?)
curl https://your-domain.com/api/v1/health/ready
```

### Prometheus(若启用)

指标在 `/metrics` 提供：

```bash
curl https://your-domain.com/metrics
```

配置 Prometheus 抓取：

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'fastapi'
    static_configs:
      - targets: ['backend:8000']
```

---

## SSL/TLS

### 用 Certbot 配合 Let's Encrypt

```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx

# Get certificate
sudo certbot --nginx -d your-domain.com

# Auto-renewal (cron)
0 12 * * * /usr/bin/certbot renew --quiet
```

---

## 备份与恢复

### 数据库备份

```bash
# Backup
docker compose exec db pg_dump -U postgres your_db > backup_$(date +%Y%m%d).sql

# Restore
docker compose exec -T db psql -U postgres your_db < backup.sql
```

### 自动备份

```bash
# /etc/cron.daily/backup-db
#!/bin/bash
BACKUP_DIR=/backups
DATE=$(date +%Y%m%d)

docker compose exec db pg_dump -U postgres your_db | gzip > $BACKUP_DIR/db_$DATE.sql.gz

# Keep only last 30 days
find $BACKUP_DIR -name "db_*.sql.gz" -mtime +30 -delete
```

---

## 安全清单

- [ ] 更改 `SECRET_KEY` 和 `API_KEY`
- [ ] 使用强数据库密码
- [ ] 全程启用 SSL/TLS
- [ ] 仅为生产域名配置 CORS
- [ ] 关闭调试模式(`DEBUG=false`)
- [ ] 在生产环境隐藏 API 文档(当 `ENVIRONMENT=production` 时自动隐藏)
- [ ] 设置防火墙规则
- [ ] 启用限流
- [ ] 配置 Sentry 做错误追踪
- [ ] 搭建日志聚合
- [ ] 定期安全更新
- [ ] 数据库备份
- [ ] 用 Logfire 监控

---

## 疑难排查

### 容器无法启动

```bash
# Check logs
docker compose logs backend

# Check health
docker compose ps
```

### 数据库连接问题

```bash
# Verify database is running
docker compose exec db pg_isready

# Check connection string
docker compose exec backend python -c "from app.core.config import settings; print(settings.DATABASE_URL)"
```

### 迁移错误

```bash
# Check current version
alembic current

# Check history
alembic history

# Create fresh migration
alembic revision --autogenerate -m "Description"
```
