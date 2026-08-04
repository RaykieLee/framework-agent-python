---
description: 调查并修复问题
---

修复问题：$ARGUMENTS

1. **理解** — search the codebase for relevant code, read the files, understand current behavior
2. **复现** — if possible, identify a test case or request that triggers the issue
3. **根因分析** — trace through Routes → Services → Repositories to find where the bug originates
4. **修复** — implement the fix following project conventions:
   - Domain exceptions in services (not HTTP errors)
   - `db.flush()` in repositories (not `commit`)
   - Type hints on all changed signatures
5. **测试** — run `cd backend && uv run pytest` to verify no regressions
6. **代码检查** — run `cd backend && uv run ruff check . --fix && uv run ruff format .`
7. **总结** — explain what was changed and why
