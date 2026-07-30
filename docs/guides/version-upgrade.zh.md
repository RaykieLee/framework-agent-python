# 升级生成的项目

当你生成一个项目后，它就属于*你*了 —— 你会修改路由、添加业务逻辑、调整配置。与此同时，脚手架本身也在持续改进。`upgrade` 命令会把这些改进**在不丢失你定制内容的前提下**合并进你现有的项目，它执行的是真正的三方合并(three-way merge),并把冲突留给你用日常的 git 工具来处理。

- **在项目内部运行**(`make upgrade`)。
- **不会静默覆盖任何内容。** 只有你改过的文件会被保留；只有脚手架改过的文件会被更新；双方都改过的文件要么自动合并，要么标记为冲突交给你解决。
- **始终可撤销。** 升级落在一个专门的 git 分支上；你的提交历史原封不动，一条命令即可全部回退。

---

## 工作原理(一张图说明)

一次升级会比较每个文件的三个版本：

| 角色   | 含义                                                              |
| ------ | ----------------------------------------------------------------- |
| BASE   | 你生成时所基于版本的脚手架，用你当初的答案渲染出来                |
| OURS   | 你当前的项目(你正在使用、已定制的代码)                          |
| THEIRS | 目标版本的脚手架，同样用你当初的答案渲染出来                      |

两份脚手架版本都用**你最初的答案**来渲染，正是这一点保证了合并的精确性：任何 BASE→OURS 的差异都确实是*你*的修改，任何 BASE→THEIRS 的差异都确实是*脚手架*的变更。工具从一个小清单文件 `.fastapi-fullstack.json` 中读取你的答案，该文件由生成器写入每个新项目。

为保证这一点成立，三棵目录树在比较之前必须以*相同方式*格式化 —— 否则格式差异会被误读为修改。升级过程会在 BASE 和 THEIRS 上复现生成器当初创建你项目时所做的事(`ruff check --fix`,然后 `ruff format`,前端则用 Prettier),而从不对 OURS 执行自动修复，因此你自己的代码在这个过程中绝不会被改写。

结果会应用到一个新分支 `template-upgrade/v<version>` 上，你像审查任何其他变更一样去审查并合并它。

---

## 前置条件

- 项目必须是**其自身 git 仓库的根目录**(`git rev-parse --show-toplevel` 指向项目目录)。升级合并的是整棵目录树，如果一个项目处于更大仓库的某个子目录里，两边的路径含义就不一致，无法对齐。遇到这种情况，工具会拒绝运行，而不是产出错误的合并。
- **干净的 git 工作区**(先把改动提交或暂存起来)。否则升级会拒绝运行，以此保证始终可撤销。`--dry-run` 是个例外：它可以在脏工作区上运行，但比较的是你已提交的 `HEAD`,所以未提交的改动不会出现在预览中(你会收到一条警告)。
- 能访问 **PyPI**(工具会从已发布的发行版中拉取脚手架版本)。
- 你的项目 **Makefile** 提供了 `make upgrade-dry-run` / `make upgrade` / `make upgrade-new-features` / `make upgrade-finalize`(用近期版本脚手架生成的项目都自带这些)。
- **前端项目：** 先在 `frontend/` 里运行 `bun install`。升级会用你已安装的 Prettier 来归一化格式，这样脚手架对 `.ts/.tsx` 文件的改动才能干净地合并；如果没有它，前端文件会退化为仅空白符归一化，可能产生虚假差异。(依赖缺失时你会收到警告 —— 升级仍会继续运行。)

---

## 场景 1 —— 项目带有清单文件(常见情况)

每个用近期版本脚手架生成的项目都包含 `.fastapi-fullstack.json`。用 `ls .fastapi-fullstack.json` 检查。如果存在，按以下步骤操作。

### 1. 从干净状态开始

```bash
cd my-project
git status            # 确认工作区是干净的
git checkout -b before-upgrade   # 可选：一个安全分支
```

### 2. 预览升级(可选但推荐)

```bash
make upgrade-dry-run             # 或者：fastapi-fullstack upgrade --dry-run
```

这会打印一份分组报告，且不改动任何内容：

```
Upgrade plan: v0.2.10 → v0.2.14

New files (3)                         ← 脚手架新增的功能/文件
New migrations (auto-added) (1)       ← 新的 Alembic 迁移
Changed migrations (review — these have probably already run) (1)
Auto-updates (template changed, you didn't) (12)
Auto-merged (both changed, merged cleanly) (2)
Kept your changes (template unchanged) (5)
Conflicts (need manual resolution) (1)
You deleted these (staying deleted) (2)  ← 你删除过的文件；脚手架仍然提供
Your files (left untouched) (8)       ← 只有你创建的文件

Manual steps after merge
  → 运行 `make db-upgrade`(新增了迁移)。
  → 依赖变更时重新运行 `uv lock` / `bun install`。
```

### 3. 应用

```bash
make upgrade                     # 或者：fastapi-fullstack upgrade
```

工具会创建分支 `template-upgrade/v<version>`,应用每一处安全变更，添加新文件和迁移，并把真正的冲突保留为标准的 git 冲突标记。结束时它会打印出确切的撤销命令。

如果想同时采纳你当前版本之后引入的**新的可选功能**(默认关闭 —— 升级不应悄悄开启你从未选择过的功能):

```bash
make upgrade-new-features    # 对每个新功能逐个提示 Yes/No
```

### 4. 解决冲突(如果有的话)

在你的 IDE 的三方合并编辑器(PyCharm、VS Code 或 `git mergetool`)中打开冲突文件。标记会显示你的版本与脚手架版本的对比：

```python
<<<<<<< ours          # 你的版本
API_TIMEOUT = 30
=======
API_TIMEOUT = 60      # 脚手架的版本
>>>>>>> theirs
```

解决后，暂存这些文件：

```bash
git add <resolved-files>
```

### 5. 收尾

```bash
make upgrade-finalize            # 或者：fastapi-fullstack upgrade finalize
```

这会检查目录树已无冲突，并**把清单文件**升级到新版本。(只要还有冲突它就拒绝运行 —— 这道安全网确保清单不会谎报你的版本。)

### 6. 运行后续步骤并合并

```bash
uv lock            # 后端依赖变更时
bun install        # 前端依赖变更时(在 frontend/ 里运行)
make db-upgrade    # 新增了迁移时
make test          # 确认没有破坏任何东西
```

然后把 `template-upgrade/v<version>` 像任何 PR 一样合并进你的主分支。

### 随时撤销 {#sui-shi-che-xiao}

```bash
git checkout -f <your-branch> \
  && git branch -D template-upgrade/v<version> \
  && rm -f .fastapi-fullstack.json.pending
```

这里的 `-f` 不是可选的。冲突未解决时，普通的 `git checkout` 会直接拒绝；而一旦解决，它反而会把暂存的升级*带到你自己的分支上*,而不是丢弃它 —— 结果是你把整个升级暂存在了 `main` 上，而分支却被删了。`upgrade` 结束时会打印这条确切的命令，用那条就好。

---

## 场景 2 —— 没有清单文件的旧项目

在清单功能出现之前生成的项目没有 `.fastapi-fullstack.json`(`ls .fastapi-fullstack.json` → 未找到)。工具无法得知它们当初是基于什么答案生成的，所以你得先创建一个清单文件，审查它，然后像场景 1 那样升级。

### 1. 重建一个候选清单

```bash
cd my-legacy-project
fastapi-fullstack upgrade recover
```

这会检查你项目的文件布局来推断哪些功能是开启的，从 README 页脚读取版本号，并写出一个**候选**文件 `.fastapi-fullstack.json.candidate`。它绝不会碰你的代码，也绝不写入真正的清单 —— 恢复是尽力而为的：

- 它能可靠地检测**布尔类型的功能开关**(RAG 开/关、是否有前端、任务队列选了哪个、AI 框架选了哪个 等等)。
- 它**无法**恢复那些不留结构性痕迹的*取值*设置 —— `db_pool_size`、`timezone`、`author_name`、`project_description`、端口、LLM/向量库的选择等等。这些会在一条警告中列出，留给你手动填写。

### 2. 审查并提升清单

打开 `.fastapi-fullstack.json.candidate`,如果检测到的 `package_version` 不对就改正它，并补上警告中标记的任何取值(在 `context` 对象内)。context 越准确，升级中的噪声就越少(context 不准确会让本没改过的文件显得"被改过" —— 安全，但会很吵)。

看起来没问题后，把它提升为正式清单并提交：

```bash
mv .fastapi-fullstack.json.candidate .fastapi-fullstack.json
git add .fastapi-fullstack.json && git commit -m "chore: add upgrade manifest"
```

### 3. 像场景 1 那样升级

至此你的项目就能自我描述了 —— 按**场景 1** 操作(`make upgrade` → 解决冲突 → `make upgrade-finalize`)。以后每次升级都是一次干净、基于清单的运行。

> **提示：** 即便手写了一份清单，也别指望那些"Kept your changes"里的文件全是你真改过的 —— 这是重建 context 不够完美所残留的结果。它是安全的(你的文件绝不会被覆盖),只是意味着能自动应用到那些文件上的脚手架更新更少。

---

## 看懂这份报告

| 区块 | 含义 | 执行的动作 |
|---|---|---|
| **New files** | 脚手架新增了一个你没有的文件。 | 添加。 |
| **New migrations** | 新的 Alembic 迁移。 | 添加(仅追加，安全)。运行 `make db-upgrade`。 |
| **Changed migrations** | 脚手架重写了一个你已有的迁移。 | 更新 —— 但它不会重新执行，所以要对照你的真实 schema 审查。 |
| **Auto-updates** | 脚手架改了你没改过的文件。 | 更新为脚手架的版本。 |
| **Auto-merged** | 双方都改动了文件，但改的地方不重叠。 | 由 git 干净地合并。 |
| **Kept your changes** | 你改了脚手架没动过的文件。 | 保持为你的版本。 |
| **Already converged** | 你和脚手架做了同样的修改。 | 无需操作。 |
| **Conflicts** | 双方改了同一行，或以不同方式添加了同一个文件。 | 保留冲突标记，交给你处理。 |
| **Your files** | 只有你创建的文件。 | 绝不触碰。 |
| **Removed by template** | 脚手架删除了一个你没改过的文件。 | 建议删除。 |
| **You deleted these** | 你删了一个脚手架仍提供且未改动的文件。 | 保持删除 —— 无需操作。 |
| **Other changes** | 上面这张表没覆盖到的任何情况。 | 审查分支。应当很少见 —— 看到的话值得反馈。 |

---

## 绝不会被触碰的内容

合并始终跳过以下这些 —— 它们从不会被读取、写入或合并：

- **密钥**:`.env`、`.env.*` —— 但已提交的示例文件(`.env.example`、`.env.sample`、`.env.template`)除外，它们会正常合并，以便某个发行版新增的配置项能到达你这里
- **锁文件**:`uv.lock`、`package-lock.json`、`bun.lock`、`bun.lockb`(依赖变更时在升级后重新生成)
- `.git/`、`node_modules/`、`.venv/`、构建产物、`__pycache__/`、缓存
- `.gitattributes` 和 git 子模块
- 系统垃圾文件：`.DS_Store`、`Thumbs.db`
- **符号链接**,无论你的还是脚手架的。被跟踪的符号链接绝不会被删除或重新暂存，脚手架也无法投递一个链接。唯一值得知道的一个例外：某个*未跟踪的*符号链接恰好处在升级要写入文件的位置，它会被那个文件替换(不会有内容顺着链接写入 —— 但链接会消失)。需要保留就先把它挪开。
- 清单文件本身(`.fastapi-fullstack.json`)—— 只由 `upgrade finalize` 来升级版本号。它的临时文件(`.pending`、`.candidate`)在新项目里会被 gitignore

Alembic 迁移**不**在排除之列 —— 它们像任何其他文件一样参与合并。它们只是有自己单独的报告区块，因为失败模式不一样：**新的**迁移会被自动添加(仅追加，安全),你自己的迁移作为客户端专属文件原样保留，而脚手架**改动过**的迁移则单列在 *Changed migrations* 下。

读一读那一节。你已有的某个迁移几乎肯定已经在数据库里执行过了，而 alembic 依据 revision id 来判断 —— 所以被重写的函数体不会重新执行，文件也就悄悄地不再描述它当初生成的那个 schema。升级仍会应用这个变更(它在一个分支上，而且发行版有时确实会修复一个真正有问题的迁移),但得由你来决定：保留它，还是在合并前 `git checkout HEAD~ -- <file>`。

---

## 清单文件 —— `.fastapi-fullstack.json`

写入每个生成的项目。它记录生成器版本和项目构建所基于的全部答案，使升级可复现。它**不包含任何密钥**(密钥形态的值在写入前会被剥离),因此可以安全提交 —— 而且你应该提交它。

```json
{
  "template": "https://github.com/vstorm-co/full-stack-ai-agent-template",
  "template_ref": "0.2.14",
  "package_version": "0.2.14",
  "generated_at": "2026-07-01T10:00:00Z",
  "context_hash": "sha256:…",
  "context": { "project_name": "…", "enable_rag": false, "...": "…" }
}
```

`upgrade finalize` 是**唯一**会更新 `package_version` 的操作 —— 而且只在干净、无冲突的解决之后 —— 所以清单绝不会声称一个你尚未完全合并的版本。

---

## 命令参考

```bash
# 在项目内部(通过 Makefile 桥接)
make upgrade-dry-run               # 预览报告，不改动任何内容
make upgrade                       # 执行升级
make upgrade-new-features          # 升级 + 采纳新增功能
make upgrade-finalize              # 解决冲突后更新清单版本号

# 额外/一次性参数通过普通 upgrade 目标的 ARGS 传入：
make upgrade ARGS=--to=0.3.0

# 底层 CLI(从任意位置用 --path 运行，或在项目目录里运行)
fastapi-fullstack upgrade [--path DIR] [--to VERSION] [--dry-run] [--with-new-features] [--force]
fastapi-fullstack upgrade finalize [--path DIR]
fastapi-fullstack upgrade recover  [--path DIR]
```

| 标志 | 作用 |
|---|---|
| `--dry-run` | 打印报告，不改动任何内容。 |
| `--to VERSION` | 升级到指定版本，而非最新版本。 |
| `--with-new-features` | 提示是否采纳你当前版本之后新增的可选功能(默认关闭)。 |
| `--force` | 若 `template-upgrade/v…` 分支已存在则重建它，**并**覆盖升级将要落到其上的未跟踪文件(不加它时，遇到冲突会中止并列出清单)。 |
| `--path DIR` | 目标项目目录(默认为当前目录)。 |

---

## 给脚手架维护者 —— `UPGRADES.yaml`

内容 diff 无法识别某个文件在版本间被**重命名/移动**,也无法识别某个 cookiecutter **变量被重命名** —— 它会把这些读成无关的删除 + 添加，从而丢失客户端的改动。把这些结构性事实记录到 `UPGRADES.yaml`(仓库根目录),每个发行版一个块：

```yaml
- version: "0.2.15"
  renames:                       # 文件/目录移动 —— 末尾 "/" 表示整个目录
    - from: "backend/app/core/config.py"
      to:   "backend/app/core/settings.py"
    - from: "backend/app/rag/"
      to:   "backend/app/knowledge/"
  variable_renames:              # 各版本间被重命名的 cookiecutter context 键
    - from: "use_pgvector"
      to:   "vector_store"
      value_map: { "true": "pgvector" }
  removed:                       # 脚手架有意删除的文件
    - "backend/app/legacy_auth.py"
  breaking:                      # 在升级报告中呈现
    - "JWT secret env var renamed SECRET_KEY → AUTH_SECRET_KEY."
  manual_steps:                  # 工具无法替客户端完成的事
    - "Run `alembic upgrade head` (new billing tables)."
```

- **renames** 在合并前把移动的文件在 BASE/OURS 之间对齐，使客户端的改动跟随文件去到新路径，而不是丢失。
- **variable_renames** 在 context 调和期间把旧答案映射到新键。
- **removed** 记录有意删除的文件，在报告中显示，让用户知道这个消失是故意的。
- **breaking** + **manual_steps** 会在升级范围内的每个版本间汇总，并在报告中显示。

### 自动记录重命名

你不必手写 `renames` 块。发行时运行：

```bash
uv run python scripts/record_renames.py            # 检测移动并写入
uv run python scripts/record_renames.py --dry-run  # 仅打印建议的块
```

它会拉取上一个已发布的脚手架版本，按内容相似度把删除和添加配对，并把新的移动写入当前版本下的 `UPGRADES.yaml`。**审查一下 diff** —— 相似度匹配偶尔会配错移动，而一个错误的 rename 会丢失客户端改动。然后手动添加任何 `breaking` / `manual_steps` / `variable_renames` —— 这些描述的是 diff 无法推断的意图。

一个 CI 守卫(`scripts/check_rename_coverage.py`,由 `.github/workflows/rename-guard.yml` 运行)会 diff 相邻的两个发行版，如果某个疑似文件移动没有对应的 `renames` 条目(或显式豁免),就**让构建失败** —— 这样被遗漏的 rename 就无法悄悄发布。失败时它会打印一个可直接粘贴的块。

---

## 疑难排查

**"No `.fastapi-fullstack.json` found — run recovery first."**
你的项目早于清单功能 —— 按**场景 2** 操作。

**"Working tree has uncommitted changes."**
先提交或暂存。升级要求干净的工作区以保持可撤销。

**"… is not the root of its git repository."**
你的项目处在一个更大仓库的子目录里。合并比较的是整棵目录树，除非项目本身就是仓库根目录，否则两边对路径含义的理解不一致 —— 于是工具宁可拒绝，也不产出错误的合并。给这个项目一个独立的仓库。

**"frontend formatting was uneven."**
某个格式化工具只跑在了三棵树中的部分树上而非全部，于是它名下的文件会显得被改动过而实际没有。已提交的 `frontend/node_modules` 没问题 —— 那个安装会被就地使用。出问题的是安装里没有 `.bin/prettier`,或者某个拒绝符号链接的平台。在 `frontend/` 里运行 `bun install` 再重试。

**"Unresolved merge conflicts remain" when finalizing.**
解决剩余冲突并 `git add` 它们，然后再运行一次 `upgrade finalize`。

**"Kept your changes" 里有很多我并没改过的文件。**
你的清单 context 没有完美匹配项目当初的生成方式(场景 2 恢复后常见)。它是安全的 —— 什么都不会被覆盖 —— 但能自动应用的脚手架更新更少。改善清单的 `context` 可以缓解。

**升级后 README 的版本页脚仍显示旧版本。**
这是预期的。渲染时有意复用原始戳记，以免在合并期间产生冲突；只有清单会在 `finalize` 时更新版本号。如果你依赖那个页脚，手动更新它。

**我想把整个升级丢掉重来。**
`git checkout -f <your-branch> && git branch -D template-upgrade/v<version> && rm -f
.fastapi-fullstack.json.pending`。保留 `-f` 和 `rm` —— 见[随时撤销](#sui-shi-che-xiao)。
