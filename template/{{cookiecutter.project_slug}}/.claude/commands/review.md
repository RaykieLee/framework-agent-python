---
description: 根据项目约定审查代码变更
---

审查当前分支中所有已暂存和未暂存的变更。

对每个变更的文件进行验证：

**架构：**
- Routes only call services, never repositories
- Services raise domain exceptions (NotFoundError, AlreadyExistsError, etc.), not HTTP exceptions
- Repositories use `db.flush()` + `db.refresh()`, never `db.commit()`
- DI uses Annotated aliases from `deps.py` (CurrentUser, *Svc), not raw `Depends()` in signatures

**模式与类型：**
- Separate Create/Update/Read/List Pydantic models
- Type hints on all function signatures (params + return)
- Modern syntax: `str | None` not `Optional[str]`
- Route return type is `-> Any`

**代码质量：**
- No debug code (print, commented-out code, TODO without issue reference)
- No security issues (SQL injection, exposed secrets, missing auth)
- Consistent naming (snake_case functions, PascalCase classes)
- Imports ordered: stdlib → third-party → local

**验证：**
1. Run `cd backend && uv run ruff check .`
2. Run `cd backend && uv run pytest` (if test files changed)

提供包含具体文件:行引用的发现，并建议修复方案。
