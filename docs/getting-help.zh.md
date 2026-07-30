# 获取帮助

## 文档

- [安装](installation.zh.md) - 安装指南
- [快速开始](guides/quick-start.zh.md) - 第一个项目上手
- [架构](architecture.zh.md) - 项目结构与模式
- [AI 智能体](ai-agent.zh.md) - AI 框架配置
- [部署](deployment.zh.md) - 生产部署指南

## GitHub

- [Issues](https://github.com/vstorm-co/full-stack-ai-agent-template/issues) - 报告 bug 或提出功能需求
- [讨论](https://github.com/vstorm-co/full-stack-ai-agent-template/discussions) - 提问和分享想法
- [Pull Requests](https://github.com/vstorm-co/full-stack-ai-agent-template/pulls) - 为项目做贡献

## 常见问题

### 我该选哪个 AI 框架？

| 使用场景 | 推荐 |
|----------|-------------|
| 类型安全的智能体，搭配 Pydantic | **PydanticAI** |
| 复杂的工作流和链 | **LangChain** |
| 有状态的智能体工作流 | **LangGraph** |

### 我该用哪个数据库？

这套脚手架使用 **PostgreSQL**(异步，SQLAlchemy 2.0 + Alembic)作为唯一支持的数据库 —— 它覆盖关系型数据、复杂查询，并同时充当 `pgvector` 的 RAG 存储。仅当你需要一个无需认证、RAG 或团队功能的无状态服务时，才传 `--database none`。

### 如何添加认证？

在项目生成时选择：

```bash
fastapi-fullstack create my_app --auth jwt     # JWT 令牌
fastapi-fullstack create my_app --auth api_key # API 密钥
fastapi-fullstack create my_app --auth both    # 两种方式都要
```

### 如何部署到生产环境？

生成的项目包含：

- `Dockerfile`,用于容器化
- `docker-compose.yml`,用于本地开发
- 可选的 Kubernetes 清单
- GitHub Actions / GitLab CI 流水线

详见[部署指南](deployment.zh.md)。

## 相关项目

- [pydantic-deep](https://github.com/vstorm-co/pydantic-deepagents) - 具备规划和子智能体能力的深度智能体框架
- [pydantic-ai](https://github.com/pydantic/pydantic-ai) - PydanticAI 智能体的基础
- [FastAPI](https://fastapi.tiangolo.com/) - 驱动后端的 Web 框架
