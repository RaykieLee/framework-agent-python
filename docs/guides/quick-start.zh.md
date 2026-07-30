# 快速开始

几分钟内让你的 AI 应用跑起来 —— 只需三条命令。

## 1. 生成项目

```bash
# 交互式向导(推荐)
fastapi-fullstack

# 或者跳过向导，使用预设
fastapi-fullstack create my_app --preset ai-agent
```

## 2. 启动全部服务

```bash
cd my_app
make bootstrap
```

`make bootstrap`(=`make dev` + `make seed`)会构建后端镜像，在 Docker 中启动 PostgreSQL 和 API,执行数据库迁移，并初始化默认管理员(`admin@example.com` / `admin123`)。它是幂等的 —— 随时可以重新运行。

!!! note "Windows 用户"
    `make` 命令需要 GNU Make。可通过 [Chocolatey](https://chocolatey.org/)(`choco install make`)安装，使用 WSL,或手动运行 Makefile 中的命令。

## 3. 启动前端

打开一个新终端：

```bash
cd frontend
bun install
bun dev
```

## 访问你的应用

| 服务 | 地址 |
|---------|-----|
| **API** | http://localhost:8000 |
| **API 文档** | http://localhost:8000/docs |
| **管理后台** | http://localhost:8000/admin |
| **前端** | http://localhost:3000 |

## 日常操作

首次 bootstrap 之后：

```bash
make dev        # 重建 + 重启(幂等，不会重新初始化管理员)
make dev-down   # 停止整套服务
make dev-logs   # 查看容器日志
```

<details>
<summary><b>在本机上运行后端(便于在 IDE 中打断点)</b></summary>

把数据库留在 Docker 里，但直接运行 API 进程：

```bash
cd my_app
make install        # uv sync + pre-commit 钩子
make docker-db      # 仅启动 PostgreSQL
make db-upgrade     # 执行迁移
make create-admin   # 交互式创建管理员
make run            # uvicorn --reload
```

</details>

## 项目 CLI

每个生成的项目都自带一个 CLI:

```bash
cd backend

# 服务器命令
uv run my_app server run --reload

# 数据库命令
uv run my_app db migrate -m "Add users"
uv run my_app db upgrade

# 用户命令
uv run my_app user create-admin
```

## 后续步骤

- [配置](configuration.zh.md) - 定制你的项目
- [AI 智能体](../ai-agent.zh.md) - 搭建 AI 框架
- [部署](../deployment.zh.md) - 部署到生产环境
