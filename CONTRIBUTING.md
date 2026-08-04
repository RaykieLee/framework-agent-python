# 贡献指南

感谢您对全栈 AI 代理模板的兴趣和贡献！

## 开发者原创证书（DCO）

本项目使用[开发者原创证书（DCO）](DCO)来确保贡献者有权提交其贡献。

提交贡献即表示您同意 DCO 的条款。您必须在每次提交时签署：

```bash
git commit -s -m "您的提交信息"
```

这会在您的提交信息中添加一行 `Signed-off-by`：

```
Signed-off-by: 您的姓名 <your@email.com>
```

如果您忘记了，可以修改上一次提交：

```bash
git commit --amend -s
```

## 如何贡献

1. **Fork** 本仓库
2. **创建分支** 用于您的功能或修复
3. **进行修改** 遵循项目规范
4. **运行测试** 确保没有破坏任何内容：
   ```bash
   uv run pytest
   uv run ruff check . --fix
   uv run ruff format .
   uv run ty check
   ```
5. **提交** 并签署（`git commit -s`）
6. **发起 Pull Request** 至 `main` 分支

## 开发环境设置

```bash
git clone https://github.com/vstorm-co/framework-agent-python.git
cd framework-agent-python
uv sync
```

## 报告问题

使用 [GitHub Issues](https://github.com/vstorm-co/framework-agent-python/issues) 报告 Bug 或请求功能。

## 行为准则

请保持尊重和建设性。我们遵循[贡献者公约](https://www.contributor-covenant.org/)。
