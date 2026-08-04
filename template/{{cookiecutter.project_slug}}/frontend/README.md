# {{ cookiecutter.project_name }} — 前端

Next.js 15（App Router）+ React 19 + TypeScript + Tailwind CSS，为 **{{ cookiecutter.project_name }}** 提供 AI 聊天界面、认证和仪表盘。

## 前提条件

- [Bun](https://bun.sh)（推荐）或 Node.js 18+
- 后端运行在 `http://localhost:{{ cookiecutter.backend_port }}` (参见项目根目录 `README.md` — `make dev`)

## 快速开始

```bash
bun install        # 安装依赖
bun dev            # 启动开发服务器于 http://localhost:{{ cookiecutter.frontend_port }}
```

或者从项目根目录通过 Docker 运行：`make dev-frontend`。

## 环境

将 `.env.example` 复制为 `.env.local`，根据需要进行调整：

| 变量 | 说明 |
|----------|-------------|
| `BACKEND_URL` | 后端 HTTP 基础 URL（服务端调用 / 代理）|
| `BACKEND_WS_URL` | 聊天流的后端 WebSocket URL |
| `NEXT_PUBLIC_AUTH_ENABLED` | 切换认证 UI（JWT/OAuth 启用时为 `true`）|
{%- if cookiecutter.enable_oauth %}
| `NEXT_PUBLIC_API_URL` | OAuth 重定向使用的公开 API URL |
{%- endif %}
{%- if cookiecutter.enable_rag %}
| `NEXT_PUBLIC_RAG_ENABLED` | 显示知识库 / RAG UI |
{%- endif %}

## 脚本

```bash
bun dev              # 开发服务器（热重载）
bun run build        # 生产构建
bun run start        # 提供生产构建服务
bun run lint         # ESLint
bun run lint:fix     # ESLint 自动修复
bun run format       # Prettier
bun run type-check   # 类型检查
bun run test:e2e     # Playwright 端到端测试
```

## 项目结构

```
src/
├── app/            # Next.js App Router — locale-prefixed routes ([locale]/…)
├── components/     # React components (chat, auth, dashboard, marketing, ui, …)
├── hooks/          # useChat, useWebSocket, and friends
├── lib/            # API clients, query keys, helpers
├── stores/         # Zustand state
├── types/          # Shared TypeScript types
├── i18n.ts         # next-intl configuration
└── middleware.ts   # locale routing + auth guards
```

## 国际化

路由以语言前缀开头 (`/{locale}/…`) 通过 [next-intl](https://next-intl-docs.vercel.app/)。
通过扩展 `i18n.ts` 并提供其消息目录来添加语言。

## 部署（Vercel）

```bash
npx vercel --prod
```

在 Vercel 控制面板中设置 `BACKEND_URL`, `BACKEND_WS_URL`, and
`NEXT_PUBLIC_AUTH_ENABLED=true`. 详情参见项目根目录 `docs/deploy.md`。
