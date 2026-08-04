 # 命令参考
 
 本项目通过两个接口提供命令：**Make** 目标用于常见工作流程，
 **项目 CLI** 用于精细控制。
 
 ## Make 命令
 
 从项目根目录运行。
 
 ### 快速开始
 
 | 命令 | 说明 |
 |---------|-------------|
{%- if cookiecutter.enable_docker %}
 | `make quickstart` | 安装依赖、启动 Docker、运行迁移、创建管理员用户 |
{%- endif %}
 | `make install` | 使用 uv 安装后端依赖{% if cookiecutter.enable_precommit %} + pre-commit 钩子{% endif %} |

 ### 开发
 
 | 命令 | 说明 |
 |---------|-------------|
 | `make run` | 启动带热重载的开发服务器 |
 | `make run-prod` | 启动生产服务器（0.0.0.0:8000） |
 | `make routes` | 显示所有已注册的 API 路由 |
 | `make test` | 运行测试，带详细输出 |
 | `make test-cov` | 运行测试，带覆盖率报告（HTML + 终端） |
 | `make format` | 使用 ruff 自动格式化代码 |
 | `make lint` | 代码检查和类型检查（ruff + ty） |
 | `make clean` | 删除缓存文件（__pycache__、.pytest_cache 等） |
 
 
 ### 数据库
 
 | 命令 | 说明 |
 |---------|-------------|
 | `make db-init` | {% if cookiecutter.use_postgresql and cookiecutter.enable_docker %}启动 PostgreSQL + 创建{% else %}创建{% endif %}初始迁移并应用 |
 | `make db-migrate` | 创建新迁移（提示输入消息） |
 | `make db-upgrade` | 应用待处理的迁移 |
 | `make db-downgrade` | 回滚上一个迁移 |
 | `make db-current` | 显示当前迁移版本 |
 | `make db-history` | 显示完整迁移历史 |

{%- if cookiecutter.use_jwt %}

 ### 用户
 
 | 命令 | 说明 |
 |---------|-------------|
 | `make create-admin` | 创建管理员用户（交互式） |
 | `make user-create` | 创建新用户（交互式） |
 | `make user-list` | 列出所有用户 |
{%- endif %}

{%- if cookiecutter.use_celery %}

 ### Celery
 
 | 命令 | 说明 |
 |---------|-------------|
 | `make celery-worker` | 启动 Celery Worker |
 | `make celery-beat` | 启动 Celery Beat 调度器 |
 | `make celery-flower` | 启动 Flower 监控 UI（端口 5555） |
{%- endif %}

{%- if cookiecutter.use_taskiq %}

 ### Taskiq
 
 | 命令 | 说明 |
 |---------|-------------|
 | `make taskiq-worker` | 启动 Taskiq Worker |
 | `make taskiq-scheduler` | 启动 Taskiq 调度器 |
{%- endif %}

{%- if cookiecutter.use_arq %}

### ARQ

 ARQ Worker 作为服务运行在开发栈中（`make dev`）。要直接运行：

```bash
uv run --directory backend arq app.worker.arq_app.WorkerSettings
```
{%- endif %}

{%- if cookiecutter.use_prefect %}

### Prefect

 Prefect 在开发栈中以两个容器运行——它们随 `make dev` 自动启动：
 
 - **`prefect-server`** — 编排 API + Web UI，地址 <http://localhost:4200>
 - **`prefect-runner`** — 注册定时部署并轮询任务
 
 Runner 是 `python -m app.worker.prefect_app`；Flow 位于 `app/worker/tasks/`。
 打开 UI 可查看 Flow 运行情况、检查日志并手动触发部署。
 默认自托管——设置 `PREFECT_API_KEY`（以及 Cloud 的 `PREFECT_API_URL`）改用 Prefect Cloud。
{%- endif %}

{%- if cookiecutter.enable_docker %}

 ### Docker（开发）
 
 | 命令 | 说明 |
 |---------|-------------|
 | `make docker-up` | 启动所有后端服务 |
 | `make docker-down` | 停止所有服务 |
 | `make docker-logs` | 跟踪后端日志 |
 | `make docker-build` | 构建后端镜像 |
 | `make docker-shell` | 在应用容器中打开 Shell |
{%- if cookiecutter.use_frontend %}
 | `make docker-frontend` | 启动前端（独立 Compose） |
 | `make docker-frontend-down` | 停止前端 |
 | `make docker-frontend-logs` | 跟踪前端日志 |
 | `make docker-frontend-build` | 构建前端镜像 |
{%- endif %}
 | `make docker-db` | 仅启动 PostgreSQL |
 | `make docker-db-stop` | 停止 PostgreSQL |
{%- if cookiecutter.enable_redis %}
 | `make docker-redis` | 仅启动 Redis |
 | `make docker-redis-stop` | 停止 Redis |
{%- endif %}

 ### Docker（使用 Traefik 的生产环境）
 
 | 命令 | 说明 |
 |---------|-------------|
 | `make docker-prod` | 启动生产环境栈 |
 | `make docker-prod-down` | 停止生产环境栈 |
 | `make docker-prod-logs` | 跟踪生产日志 |
 | `make docker-prod-build` | 构建生产镜像 |

{%- if cookiecutter.use_frontend %}

 ### Vercel（前端部署）
 
 | 命令 | 说明 |
 |---------|-------------|
 | `make vercel-deploy` | 部署前端到 Vercel |
{%- endif %}
{%- endif %}

---

 ## 项目 CLI
 
 所有项目 CLI 命令通过以下方式调用：

```bash
cd backend
uv run {{ cookiecutter.project_slug }} <group> <command> [options]
```

 ### 服务器命令

```bash
 uv run {{ cookiecutter.project_slug }} server run              # 启动开发服务器
 uv run {{ cookiecutter.project_slug }} server run --reload     # 带热重载
 uv run {{ cookiecutter.project_slug }} server run --port 9000  # 自定义端口
 uv run {{ cookiecutter.project_slug }} server routes           # 显示所有已注册路由
```


 ### 数据库命令

```bash
uv run {{ cookiecutter.project_slug }} db init                  # Run all migrations
uv run {{ cookiecutter.project_slug }} db migrate -m "message"  # Create new migration
uv run {{ cookiecutter.project_slug }} db upgrade               # Apply pending migrations
uv run {{ cookiecutter.project_slug }} db upgrade --revision e3f  # Upgrade to specific revision
uv run {{ cookiecutter.project_slug }} db downgrade             # Rollback last migration
uv run {{ cookiecutter.project_slug }} db downgrade --revision base  # Rollback to start
uv run {{ cookiecutter.project_slug }} db current               # Show current revision
uv run {{ cookiecutter.project_slug }} db history               # Show migration history
```

{%- if cookiecutter.use_jwt %}

 ### 用户命令

```bash
 # 创建用户（交互式提示输入邮箱/密码）
 uv run {{ cookiecutter.project_slug }} user create
 
 # 非交互式创建用户
 uv run {{ cookiecutter.project_slug }} user create --email user@example.com --password secret
 
 # 使用指定角色创建用户
 uv run {{ cookiecutter.project_slug }} user create --email admin@example.com --password secret --role admin
 
 # 使用超级用户标志创建用户
 uv run {{ cookiecutter.project_slug }} user create --email admin@example.com --password secret --superuser
 
 # 创建管理员（快捷方式）
 uv run {{ cookiecutter.project_slug }} user create-admin --email admin@example.com --password secret
 
 # 更改用户角色
 uv run {{ cookiecutter.project_slug }} user set-role user@example.com --role admin
 
 # 列出所有用户
 uv run {{ cookiecutter.project_slug }} user list
```
{%- endif %}

{%- if cookiecutter.use_celery %}

 ### Celery 命令

```bash
 uv run {{ cookiecutter.project_slug }} celery worker                    # 启动 Worker
 uv run {{ cookiecutter.project_slug }} celery worker --loglevel debug   # 调试日志级别
 uv run {{ cookiecutter.project_slug }} celery worker --concurrency 8    # 8 个 Worker 进程
 uv run {{ cookiecutter.project_slug }} celery beat                      # 启动调度器
 uv run {{ cookiecutter.project_slug }} celery flower                    # 启动 Flower UI
 uv run {{ cookiecutter.project_slug }} celery flower --port 5556        # 自定义 Flower 端口
```
{%- endif %}

{%- if cookiecutter.use_taskiq %}

 ### Taskiq 命令

```bash
 uv run {{ cookiecutter.project_slug }} taskiq worker                # 启动 Worker
 uv run {{ cookiecutter.project_slug }} taskiq worker --workers 4    # 4 个 Worker 进程
 uv run {{ cookiecutter.project_slug }} taskiq worker --reload       # 带自动重载（开发）
 uv run {{ cookiecutter.project_slug }} taskiq scheduler             # 启动定时调度器
```
{%- endif %}

 ### 自定义命令
 
 自定义命令从 `app/commands/` 自动发现。通过以下方式运行：

```bash
uv run {{ cookiecutter.project_slug }} cmd <command-name> [options]
```

{%- if cookiecutter.enable_rag %}

 ### RAG 命令
 
 所有 RAG 命令都是通过 `cmd` 调用的自定义命令：

 #### 文档摄取

```bash
 # 摄取单个文件
 uv run {{ cookiecutter.project_slug }} cmd rag-ingest ./docs/guide.pdf
 
 # 摄取目录
 uv run {{ cookiecutter.project_slug }} cmd rag-ingest ./docs/
 
 # 递归摄取到特定集合
 uv run {{ cookiecutter.project_slug }} cmd rag-ingest ./docs/ --collection knowledge --recursive
 
 # 带同步模式的摄取
 uv run {{ cookiecutter.project_slug }} cmd rag-ingest ./docs/ --sync-mode new_only
 uv run {{ cookiecutter.project_slug }} cmd rag-ingest ./docs/ --sync-mode update_only
 
 # 跳过替换现有文档
 uv run {{ cookiecutter.project_slug }} cmd rag-ingest ./docs/ --no-replace
```

 #### 搜索

```bash
 # 搜索默认集合
 uv run {{ cookiecutter.project_slug }} cmd rag-search "what is fastapi"
 
 # 搜索特定集合
 uv run {{ cookiecutter.project_slug }} cmd rag-search "deployment guide" --collection docs
 
 # 获取更多结果
 uv run {{ cookiecutter.project_slug }} cmd rag-search "deployment" --top-k 10
```

 #### 集合管理

```bash
 # 列出所有集合及其统计信息
 uv run {{ cookiecutter.project_slug }} cmd rag-collections
 
 # 显示整体 RAG 系统统计信息
 uv run {{ cookiecutter.project_slug }} cmd rag-stats
 
 # 删除集合（需确认）
 uv run {{ cookiecutter.project_slug }} cmd rag-drop my_collection
 
 # 无需确认直接删除
 uv run {{ cookiecutter.project_slug }} cmd rag-drop my_collection --yes
```

{%- if cookiecutter.enable_google_drive_ingestion %}

 #### Google Drive 同步

```bash
 # 从 Google Drive 根目录同步
 uv run {{ cookiecutter.project_slug }} cmd rag-sync-gdrive --collection docs
 
 # 从特定文件夹同步
 uv run {{ cookiecutter.project_slug }} cmd rag-sync-gdrive --collection docs --folder-id abc123
```
{%- endif %}

{%- if cookiecutter.enable_s3_ingestion %}

 #### S3/MinIO 同步

```bash
 # 从 S3 Bucket 根目录同步
 uv run {{ cookiecutter.project_slug }} cmd rag-sync-s3 --collection docs
 
 # 从特定前缀（文件夹）同步
 uv run {{ cookiecutter.project_slug }} cmd rag-sync-s3 --collection docs --prefix documents/
 
 # 从特定 Bucket 同步
 uv run {{ cookiecutter.project_slug }} cmd rag-sync-s3 --collection docs --bucket my-bucket
```
{%- endif %}


 #### 同步源管理

```bash
 # 列出已配置的同步源
 uv run {{ cookiecutter.project_slug }} cmd rag-sources
 
 # 添加新的同步源
 uv run {{ cookiecutter.project_slug }} cmd rag-source-add \
     --name "我的 Drive" \
     --type gdrive \
     --collection docs \
     --config '{"folder_id": "abc123"}' \
     --sync-mode new_only \
     --schedule 60
 
 # 删除同步源
 uv run {{ cookiecutter.project_slug }} cmd rag-source-remove <source-id>
 uv run {{ cookiecutter.project_slug }} cmd rag-source-remove <source-id> --yes  # 跳过确认
 
 # 触发特定源的同步
 uv run {{ cookiecutter.project_slug }} cmd rag-source-sync <source-id>
 
 # 触发所有活跃源的同步
 uv run {{ cookiecutter.project_slug }} cmd rag-source-sync --all
```
{%- endif %}

 ## 添加自定义命令

Commands are auto-discovered from `app/commands/`. Create a new file:

```python
# app/commands/my_command.py
import click
from app.commands import command, success, error

 @command("my-command", help="描述该命令的功能")
 @click.option("--name", "-n", required=True, help="名称参数")
 def my_command(name: str):
     """你的命令逻辑在此。"""
     success(f"完成：{name}")
```

 运行：

```bash
uv run {{ cookiecutter.project_slug }} cmd my-command --name test
```

 更多详情参见 `docs/adding_features.md`。
