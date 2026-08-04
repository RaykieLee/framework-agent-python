 # 为 {{ cookiecutter.project_name }} 贡献代码
 
 ## 开发环境搭建
 
 ```bash
 # 后端（基于 uv）
 cd backend
 uv sync                    # 安装所有依赖，包括开发依赖
 cp .env.example .env       # 然后填写所需变量（参见 ENV_VARS.md）
 uv run uvicorn app.main:app --reload --port {{ cookiecutter.backend_port }}
 uv run alembic upgrade head  # 应用迁移
 
 {%- if cookiecutter.use_frontend %}
 # 前端（基于 bun）
 cd ../frontend
 bun install
 bun dev                    # http://localhost:{{ cookiecutter.frontend_port }}
 {%- endif %}
 {%- if cookiecutter.enable_docker %}
 
 # 或全部通过 Docker 运行
 docker compose up
 {%- endif %}
 ```
 
 ## 代码风格
 
 - **Python：** ruff（`uv run ruff check . --fix && uv run ruff format .`）。行长度 120。
 - **类型提示：** 现代语法（`str | None`、`list[X]`、`dict[str, Any]`）。路由签名中使用 `Annotated[T, Depends(...)]` 进行依赖注入。
{%- if cookiecutter.use_frontend %}
 - **TypeScript：** 严格模式，除非外部 API 已定义类型，否则不使用 `any`。ESLint + Prettier（运行 `bun run lint`）。
{%- endif %}
 - **导入顺序：** 标准库 → 第三方 → 本地，之间用空行分隔。使用 `TYPE_CHECKING` 块打破循环引用。
 - **日期时间：** `datetime.now(UTC)`，而非 `datetime.utcnow()`。
 - **比较：** 令牌/密钥使用 `secrets.compare_digest()`（常量时间比较）。

 ## 测试
{% if cookiecutter.enable_pytest %}
```bash
cd backend
 uv run pytest                              # 所有后端测试
 uv run pytest tests/test_file.py::test -v  # 单个测试
 uv run pytest -k "name_substring" -v       # 按名称模式
 uv run pytest --cov=app                    # 带覆盖率
```
{%- if cookiecutter.use_frontend %}

```bash
cd frontend
 bun test                  # vitest
 bunx tsc --noEmit         # 类型检查（不输出文件）
```
{%- endif %}
{%- else %}
 本项目未生成测试。运行 `uv run python -m unittest discover` 来执行你添加的任何临时测试。
{%- endif %}

 ## 架构规则
 
 - **路由层**绝不直接导入仓库层。始终通过服务层访问。
 - **服务层**抛出领域异常（`NotFoundError`、`AlreadyExistsError`）——"未找到"情况绝不返回 `None`。
 - **仓库层**使用 `db.flush()` + `db.refresh()`，绝不能使用 `db.commit()`（会话在 `get_db_session` 中自动提交）。
 - **Pydantic 模式：** 每个操作分离 `*Create`、`*Update`、`*Read`、`*List`。
 - **迁移：** 每个逻辑更改对应一个 Alembic 修订版本；绝不编辑已合并的迁移。

 查看 `docs/architecture.md` 获取完整的分层架构规则。
{%- if cookiecutter.enable_precommit %}

 ## Pre-commit
 
 通过 `.pre-commit-config.yaml` 配置。安装一次：
 
 ```bash
 uv run pre-commit install
 ```
 
 每次提交时将运行 ruff +（如果存在前端则运行前端代码检查）。仅在修复 Hook 错误时使用 `--no-verify` 跳过。
{%- endif %}

 ## 拉取请求检查清单
 
 - [ ] `uv run ruff check . && uv run ruff format --check .` 通过
{%- if cookiecutter.use_frontend %}
 - [ ] `cd frontend && bunx tsc --noEmit` 通过
{%- endif %}
{%- if cookiecutter.enable_pytest %}
 - [ ] 新代码路径添加了测试；`uv run pytest` 通过
{%- endif %}
 - [ ] 如果模式变更：提交了 Alembic 迁移（`uv run alembic revision --autogenerate -m "..."`）
 - [ ] 如果添加了新的环境变量，已更新 `ENV_VARS.md`
 - [ ] 已更新 `CHANGELOG.md`（如适用）
