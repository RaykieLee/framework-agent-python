---
name: channel-bot
description: 处理消息渠道机器人（Telegram / Slack） — register a bot, route inbound messages through the AI agent, handle webhooks vs polling, or add a new channel adapter. 在将聊天集成到消息平台时使用 or debugging bot delivery.
---

# 消息渠道（Telegram / Slack）

Channels are a **thick service** at `backend/app/services/channels/`: per-platform adapters plus a router that funnels inbound messages into the **same agent pipeline** as the web chat.

## 布局

| File | Responsibility |
|------|---------------|
| `base.py` | Shared channel adapter interface |
| `telegram.py` | Telegram adapter (aiogram v3) |
| `slack.py` | Slack adapter (Events API + Socket Mode) |
| `router.py` | Maps an inbound platform message → conversation/session → agent run → reply |
| `chart_render.py` | Renders chart tool output as PNG for channels |

Bots are stored in the DB (`channel_bot`), with per-user identity (`channel_identity`) and per-thread session (`channel_session`) tables. Bot tokens are encrypted at rest with `CHANNEL_ENCRYPTION_KEY` (Fernet).

## 注册 / 管理机器人

```bash
uv run {{ cookiecutter.project_slug }} cmd channel ...   # see `cmd channel --help`
```

## Webhook vs 轮询

- **Polling (dev):** the adapter long-polls the platform — no public URL needed.
- **Webhook (prod):** the platform POSTs to `POST /api/v1/telegram/{bot_id}/webhook` / the Slack events endpoint. Verify the signature/secret (HMAC for Telegram, signing secret for Slack) before processing.

## 添加新的渠道适配器

1. Implement an adapter in `services/channels/<platform>.py` against the `base.py` interface (parse inbound → normalized message; send outbound).
2. Wire it into `router.py` so inbound messages reach the agent and replies stream back.
3. Add a webhook route under `api/routes/v1/` (signature-verified) and/or a polling entrypoint.
4. Reuse the existing conversation/session model — don't fork the agent pipeline.

## 规则

- Inbound messages flow through `router.py` into the **same** agent/session pipeline as web chat — don't duplicate agent logic per platform.
- Always verify webhook signatures before acting on a payload.
- Store tokens encrypted (`CHANNEL_ENCRYPTION_KEY`); never log or echo them.
- Respect per-group/per-thread concurrency controls already in the adapters.
