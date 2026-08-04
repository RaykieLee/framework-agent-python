# Issue tracker: Local Markdown

本仓库的任务和规格使用 `.scratch/` 下的 Markdown 文件管理。

## Conventions

- 每项功能一个目录：`.scratch/<feature-slug>/`
- 功能规格为 `.scratch/<feature-slug>/spec.md`
- 实施任务放在 `.scratch/<feature-slug>/issues/<NN>-<slug>.md`
- 每张 ticket 一个文件，按依赖顺序从 `01` 编号
- `Status:` 记录 triage 状态
- `Blocked by:` 记录阻塞 ticket
- 评论和讨论追加到文件末尾的 `## Comments`

## Publishing

当工程技能要求发布任务时，在相应 `.scratch/<feature-slug>/` 下创建 Markdown 文件。

## Fetching

当工程技能要求读取任务时，读取用户给出的本地文件路径或编号对应的文件。
