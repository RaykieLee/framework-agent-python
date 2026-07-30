# 开发指南

本指南介绍如何为生成的项目搭建本地开发环境。

## 前置条件

- **Python 3.11+**(推荐 3.12)
- **uv** —— 快速的 Python 包管理器
- **Docker**(可选，用于数据库)
- **Bun** —— JavaScript 运行时(用于前端)
- **PostgreSQL**(通过 `make dev` 用 Docker 运行)

---

## 快速开始

### 1. 生成项目

```bash
# Interactive mode
fastapi-fullstack new

# Or quick mode
fastapi-fullstack create my_project --database postgresql --auth jwt
```

### 2. 后端搭建

```bash
cd my_project/backend

# Install dependencies
uv sync

# Copy environment file
cp .env.example .env

# Start PostgreSQL (Docker)
docker run -d \
  --name postgres \
  -e POSTGRES_PASSWORD=secret \
  -e POSTGRES_DB=my_project \
  -p 5432:5432 \
  postgres:16-alpine

# Run migrations
alembic upgrade head

# Create admin user
uv run python -m cli.commands user create-admin --email admin@example.com

# Start development server
uv run uvicorn app.main:app --reload
```

### 3. 前端搭建(若启用)

```bash
cd my_project/frontend

# Install dependencies
bun install

# Start development server
bun dev
```

### 4. 访问应用

- **后端 API**:<http://localhost:8000>
- **API 文档**:<http://localhost:8000/docs>
- **前端**:<http://localhost:3000>(若启用)

---

## 使用 Docker Compose

用于完整的开发环境：

```bash
cd my_project

# Start all services
docker compose up -d

# View logs
docker compose logs -f

# Run migrations
docker compose exec backend alembic upgrade head

# Stop services
docker compose down
```

### 服务

| 服务 | 端口 | 说明 |
|---------|------|-------------|
| backend | 8000 | FastAPI 应用 |
| frontend | 3000 | Next.js 应用 |
| db | 5432 | PostgreSQL 数据库 |
| redis | 6379 | Redis 缓存(若启用) |
| mailcatcher | 1080 | 邮件测试界面 |

---

## Environment Variables

### 后端(.env)

```bash
# Application
ENVIRONMENT=local
DEBUG=true
PROJECT_NAME=my_project

# Database
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=secret
POSTGRES_DB=my_project

# Auth
SECRET_KEY=change-me-in-production-use-openssl-rand-hex-32
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_MINUTES=10080

# Logfire (optional)
LOGFIRE_TOKEN=

# Redis (if enabled)
REDIS_HOST=localhost
REDIS_PORT=6379

# AI Agent (if enabled)
OPENAI_API_KEY=sk-...
AI_MODEL=gpt-4o-mini
```

### 前端(.env.local)

```bash
# Backend URL (server-side only - not exposed to browser)
BACKEND_URL=http://localhost:8000

# WebSocket URL for real-time features
BACKEND_WS_URL=ws://localhost:8000

# Authentication (set to true when JWT or OAuth is enabled)
NEXT_PUBLIC_AUTH_ENABLED=true

# RAG (Retrieval Augmented Generation)
NEXT_PUBLIC_RAG_ENABLED=true

# Public API URL for OAuth redirects (exposed to browser)
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## 项目 CLI

生成的项目自带一个 CLI,用于常见任务：

```bash
# Show all commands
uv run python -m cli.commands --help

# Server commands
uv run python -m cli.commands server run --reload
uv run python -m cli.commands server routes

# Database commands
uv run python -m cli.commands db init
uv run python -m cli.commands db migrate -m "Add table"
uv run python -m cli.commands db upgrade
uv run python -m cli.commands db downgrade

# User commands
uv run python -m cli.commands user create
uv run python -m cli.commands user create-admin
uv run python -m cli.commands user list

# Custom commands
uv run python -m cli.commands cmd seed --count 100
```

---

## 使用 Makefile

常用命令可通过 Makefile 使用：

```bash
# Install dependencies
make install
make install-dev

# Run development server
make run

# Testing
make test
make test-cov

# Code quality
make lint
make format
make typecheck

# Database
make db-init
make db-migrate
make db-upgrade

# Docker
make docker-build
make docker-up
make docker-down
```

---

## 测试

### 后端测试

```bash
cd backend

# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=term-missing

# Run specific test file
pytest tests/api/test_items.py -v

# Run specific test
pytest tests/api/test_items.py::test_create_item -v

# Run with verbose output
pytest -v --tb=short

# Run async tests only
pytest -m asyncio
```

### 前端测试

```bash
cd frontend

# Unit tests (Vitest)
bun test
bun test:run
bun test:coverage

# E2E tests (Playwright)
bun test:e2e
bun test:e2e:ui
bun test:e2e:headed
```

### 测试配置

```python
# tests/conftest.py
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.main import app
from app.db.base import Base
from app.api.deps import get_db


# Test database
TEST_DATABASE_URL = "postgresql+asyncpg://postgres:secret@localhost:5432/test_db"

engine = create_async_engine(TEST_DATABASE_URL)
TestingSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


@pytest.fixture(scope="function")
async def db_session():
    """Create a fresh database session for each test."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestingSessionLocal() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def client(db_session):
    """Create test client with database override."""
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client

    app.dependency_overrides.clear()
```

---

## 代码质量

### Ruff(代码检查与格式化)

```bash
# Check for issues
ruff check .

# Fix auto-fixable issues
ruff check . --fix

# Format code
ruff format .

# Check formatting
ruff format . --check
```

### Mypy(类型检查)

```bash
# Run type checker
mypy app

# With specific options
mypy app --strict --ignore-missing-imports
```

### Pre-commit 钩子

```bash
# Install hooks
pre-commit install

# Run on all files
pre-commit run --all-files

# Update hooks
pre-commit autoupdate
```

在 `.pre-commit-config.yaml` 中的配置：

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.8.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.13.0
    hooks:
      - id: mypy
        additional_dependencies: [pydantic]
```

---

## 数据库管理

### PostgreSQL

```bash
# Start PostgreSQL container
docker run -d \
  --name postgres \
  -e POSTGRES_PASSWORD=secret \
  -e POSTGRES_DB=my_project \
  -p 5432:5432 \
  postgres:16-alpine

# Connect to database
docker exec -it postgres psql -U postgres -d my_project

# Stop container
docker stop postgres
docker rm postgres
```

### 迁移(Alembic)

```bash
# Create migration
alembic revision --autogenerate -m "Add users table"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# Rollback to specific revision
alembic downgrade abc123

# Show current revision
alembic current

# Show history
alembic history
```

### 重置数据库

```bash
# Drop and recreate database
docker exec -it postgres psql -U postgres -c "DROP DATABASE my_project;"
docker exec -it postgres psql -U postgres -c "CREATE DATABASE my_project;"

# Re-run migrations
alembic upgrade head
```

---

## 调试

### FastAPI

```python
# Add breakpoint
breakpoint()

# Or use debugpy for remote debugging
import debugpy
debugpy.listen(5678)
debugpy.wait_for_client()
```

### VS Code 启动配置

```json
// .vscode/launch.json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "FastAPI",
      "type": "debugpy",
      "request": "launch",
      "module": "uvicorn",
      "args": ["app.main:app", "--reload"],
      "cwd": "${workspaceFolder}/backend",
      "envFile": "${workspaceFolder}/backend/.env"
    }
  ]
}
```

### Logfire

在 Logfire 控制台查看 trace 和日志：

```bash
# Set token
export LOGFIRE_TOKEN=your-token

# Run with Logfire enabled
uv run uvicorn app.main:app --reload
```

---

## 热重载

### 后端

文件变更时，开发服务器会自动重载：

```bash
uvicorn app.main:app --reload
```

### 前端

Next.js Fast Refresh 默认启用：

```bash
bun dev
```

---

## IDE 配置

### VS Code 扩展

推荐的扩展：

- **Python** —— Microsoft Python 扩展
- **Pylance** —— 类型检查和 IntelliSense
- **Ruff** —— 代码检查和格式化
- **Python Test Explorer** —— 测试发现与运行
- **GitLens** —— Git 集成

### 设置

```json
// .vscode/settings.json
{
  "[python]": {
    "editor.defaultFormatter": "charliermarsh.ruff",
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
      "source.fixAll.ruff": "explicit",
      "source.organizeImports.ruff": "explicit"
    }
  },
  "python.analysis.typeCheckingMode": "basic",
  "python.testing.pytestEnabled": true,
  "python.testing.pytestArgs": ["tests"]
}
```

### PyCharm

1. 在 PyCharm 中打开项目
2. 把 Python 解释器设为虚拟环境
3. 把 `app` 标记为 Sources Root
4. 把 `tests` 标记为 Test Sources Root
5. 启用 pytest 作为测试运行器

---

## 常见问题

### "ModuleNotFoundError: No module named 'app'"

```bash
# Ensure you're in the backend directory
cd backend

# Or set PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

### 数据库 "Connection refused"

```bash
# Check if PostgreSQL is running
docker ps | grep postgres

# Start if not running
docker start postgres
```

### Docker "Permission denied"

```bash
# Add user to docker group
sudo usermod -aG docker $USER

# Log out and back in, or run
newgrp docker
```

### Alembic "Target database is not up to date"

```bash
# Check current revision
alembic current

# Stamp as current (if database was created manually)
alembic stamp head
```
