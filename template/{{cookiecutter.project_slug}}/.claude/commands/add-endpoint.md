---
description: 搭建一个新的 API 端点，包含完整分层
---

创建新的 API 端点：$ARGUMENTS

Follow the project's layered architecture. Create files in this order:

1. **模式** (`backend/app/schemas/<entity>.py`):
   - Inherit `BaseSchema` (and `TimestampSchema` for Read)
   - Create `*Create`, `*Update`, `*Read`, `*List` models
   - Use `Field()` with constraints, `EmailStr` where applicable

2. **数据库模型** (`backend/app/db/models/<entity>.py`):
   - Inherit `Base, TimestampMixin`
   - Use `Mapped[type]` + `mapped_column()`
   - Add `__repr__`, relationships with `cascade="all, delete-orphan"`

3. **仓库** (`backend/app/repositories/<entity>_repo.py`):
   - Stateless async functions: `get_by_id`, `get_multi`, `create`, `update`, `delete`
   - Use `db.flush()` + `db.refresh()`, keyword-only args after `db`

4. **服务** (`backend/app/services/<entity>.py`):
   - Class with `__init__(self, db: AsyncSession)`
   - Raise `NotFoundError`, `AlreadyExistsError` as appropriate

5. **依赖注入** (`backend/app/api/deps.py`):
   - Add factory function and `Annotated` alias: `EntitySvc = Annotated[EntityService, Depends(get_entity_service)]`

6. **路由** (`backend/app/api/routes/v1/<entity>.py`):
   - CRUD: GET list, GET by id, POST (201), PATCH, DELETE (204)
   - Use DI aliases, `response_model`, `-> Any` return type

7. **注册**路由到 `backend/app/api/routes/v1/__init__.py`

8. **迁移**: `cd backend && uv run alembic revision --autogenerate -m "Add <entity> table"`

9. **测试** (`backend/tests/`): mirror source structure

10. 代码检查: `cd backend && uv run ruff check . --fix && uv run ruff format .`
