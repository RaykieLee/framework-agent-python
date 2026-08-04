# 安装

## 环境要求

- Python 3.11+
- [uv](https://docs.astral.sh/uv/)(推荐)或 pip

## 安装 framework-agent-python

=== "uv(推荐)"

    ```bash
    uv tool install framework-agent-python
    ```

=== "pip"

    ```bash
    pip install framework-agent-python
    ```

=== "pipx"

    ```bash
    pipx install framework-agent-python
    ```

## 验证安装

```bash
framework-agent-python --version
```

## 创建你的第一个项目

生成项目，然后用一条命令把整个后端启动起来：

```bash
# 1. 生成你的项目 —— 只需回答向导的提示
framework-agent-python

# 2. 后端 + PostgreSQL 启动，迁移已执行，默认管理员已初始化
cd my_app
make bootstrap

# 3. 前端(在第二个终端里)
cd frontend && bun install && bun dev
```

这就完成了 —— 后端在 <http://localhost:8000>,API 文档在 `/docs`,前端在 <http://localhost:3000>,管理员登录账号 `admin@example.com` / `admin123`。

`make bootstrap`(=`make dev` + `make seed`)会构建后端镜像、启动 Docker 服务栈、等待 PostgreSQL 就绪、执行迁移并初始化管理员用户。它是幂等的 —— 随时可以重新运行。

### 其他生成方式

```bash
# 用显式参数进行非交互式生成
framework-agent-python create my_app --database postgresql --frontend nextjs

# 预设(运行 `framework-agent-python templates` 查看完整列表)
framework-agent-python create my_app --preset ai-agent

# 最简项目
framework-agent-python create my_app --minimal
```

## 可用预设

| 预设 | 说明 |
|--------|-------------|
| `--preset production` | 完整生产配置，含 Redis、Sentry、Kubernetes、Prometheus |
| `--preset ai-agent` | AI 智能体，含 WebSocket 流式输出和会话持久化 |
| `--preset production-saas` | SaaS 配置：计费、团队和管理后台 |
| `--minimal` | 无任何附加功能的最简项目 |

## 后续步骤

- [快速开始](guides/quick-start.zh.md) - 搭建你的开发环境
- [配置](guides/configuration.zh.md) - 了解配置选项
- [AI 智能体](ai-agent.zh.md) - 配置 AI 框架
