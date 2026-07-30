# 截图

带你看看生成项目开箱即用的样子 —— 聊天、营销站、控制台、账单、管理和编排。

!!! tip "浅色 / 深色"
    许多截图同时提供**两种主题**。使用顶部栏的亮度切换(☀️ / 🌙),下方图片会随之自动切换。

## AI 聊天

聊天界面通过 WebSocket 流式传输，并把每个工具调用渲染为专门定制的卡片，而非原始的 JSON 转储。

**计划与任务** —— 输入框上方有一个吸顶的计划/任务清单，随智能体工作实时更新，并带有内嵌的推理指示器。

![聊天计划与任务](screenshots/chat_tasks.png){.shot}

**子智能体** —— 当工作被委派时，实时信息流和侧边栏会显示每个子智能体的状态、流式消息和最终结果。

![聊天子智能体](screenshots/chat_subagents.png){.shot}

**图表** —— `create_chart` 工具会在行内渲染交互式、随主题变化的柱状图 / 面积图 / 折线图 / 饼图 / 散点图。

![聊天图表](screenshots/chat_graphs.png){.shot}

**代码执行** —— 可选的 `run_python` 工具会在一个可折叠卡片中并排展示执行的代码及其输出(或错误)。

![聊天 Python 代码执行](screenshots/chat_python_code.png){.shot}

**询问用户** —— 智能体可以暂停以提出澄清问题，在你回答后继续。

![聊天询问用户工具](screenshots/chat_ask_user.png){.shot}

**推理与已回答的问题** —— 干净的思考视图加上已回答问题的历史，让长对话保持可读。

![聊天推理与已回答问题](screenshots/chat_answered_questions_and_thinking.png){.shot}

## 营销站

通过 `enable_marketing_site` 选项生成 —— 一个可以直接上线的完整公开站点。

**主视觉区**

![Landing hero](screenshots/landing_hero.png){.shot}

**完整落地页**

![Landing page](screenshots/landing_full.png){.shot}

**定价** —— 按月/按年切换；接入 Stripe 后会拉取实时的套餐数据。

![定价](screenshots/landing_pricing.png){.shot}

**博客** —— 仓库中的 MDX 文章，无需 CMS。

![博客](screenshots/blogs.png){.shot}

## 认证

**登录** —— 分屏布局，带 Google OAuth 和邮箱/密码。

![登录](screenshots/login.png){.shot}

**注册**

![注册](screenshots/register.png){.shot}

**重置密码**

![重置密码](screenshots/reset_password.png){.shot}

## 控制台

工作区概览，带迷你统计卡片、用量时间线、近期动态和团队信息。

![控制台 — 浅色](screenshots/dashboard_light.png#only-light){.shot}
![控制台 — 深色](screenshots/dashboard_dark.png#only-dark){.shot}

## 团队与组织

**工作区** —— 你所属的每个组织，带套餐等级和角色。

![组织 — 浅色](screenshots/organizations_light.png#only-light){.shot}
![组织 — 深色](screenshots/organizations_dark.png#only-dark){.shot}

**团队管理** —— 成员、角色和邀请。

![组织 — 浅色](screenshots/organization_light.png#only-light){.shot}
![组织 — 深色](screenshots/organization_dark.png#only-dark){.shot}

## 知识库

**知识库** —— 作用域限定在工作区的 RAG 集合；可选择在聊天中启用哪些。

![知识库 — 浅色](screenshots/knowledge_bases_light.png#only-light){.shot}
![知识库 — 深色](screenshots/knowledge_bases_dark.png#only-dark){.shot}

**文档与同步源** —— 预览或下载任意文件，并管理已连接的同步源(Google Drive、S3/MinIO),支持手动触发和逐次运行的日志。

![知识库来源 — 浅色](screenshots/knowledge_base_source_light.png#only-light){.shot}
![知识库来源 — 深色](screenshots/knowledge_base_source_dark.png#only-dark){.shot}

## 账单与用量

**概览** —— 套餐、席位、存储用量和快捷链接。"在 Stripe 中管理"会打开客户门户。

![账单概览 — 浅色](screenshots/billing_and_usage_light.png#only-light){.shot}
![账单概览 — 深色](screenshots/billing_and_usage_dark.png#only-dark){.shot}

**用量** —— 每日额度消耗和调用次数图表，外加按模型划分的 token 用量。

![账单用量 — 浅色](screenshots/billing_usage_light.png#only-light){.shot}
![账单用量 — 深色](screenshots/billing_usage_dark.png#only-dark){.shot}

**额度** —— 余额和不可变的交易账本。

![账单额度 — 浅色](screenshots/billing_credits_light.png#only-light){.shot}
![账单额度 — 深色](screenshots/billing_credits_dark.png#only-dark){.shot}

**订阅与发票**

![账单订阅 — 浅色](screenshots/billing_subscription_light.png#only-light){.shot}
![账单订阅 — 深色](screenshots/billing_subscription_dark.png#only-dark){.shot}
![账单发票 — 浅色](screenshots/billing_invoices_light.png#only-light){.shot}
![账单发票 — 深色](screenshots/billing_invoices_dark.png#only-dark){.shot}

## 个人资料与设置

**个人资料**

![个人资料 — 浅色](screenshots/profile_light.png#only-light){.shot}
![个人资料 — 深色](screenshots/profile_dark.png#only-dark){.shot}

**账户与安全**

![账户 — 浅色](screenshots/account_light.png#only-light){.shot}
![账户 — 深色](screenshots/account_dark.png#only-dark){.shot}

**斜杠命令** —— 自定义聊天中的 `/command` 面板。

![斜杠命令 — 浅色](screenshots/commands_light.png#only-light){.shot}
![斜杠命令 — 深色](screenshots/commands_dark.png#only-dark){.shot}

**外观** —— 主题切换器和品牌色预设。

![外观 — 浅色](screenshots/appearance_light.png#only-light){.shot}
![外观 — 深色](screenshots/appearance_dark.png#only-dark){.shot}

**通知**

![通知 — 浅色](screenshots/notifications_light.png#only-light){.shot}
![通知 — 深色](screenshots/notifications_dark.png#only-dark){.shot}

## 管理后台

需要 `admin` 角色。

**概览** —— 用户、活跃会话、对话、MRR,以及近期动态信息流。

![管理概览 — 浅色](screenshots/admin_overview_light.png#only-light){.shot}
![管理概览 — 深色](screenshots/admin_overview_dark.png#only-dark){.shot}

**用户管理**

![管理用户 — 浅色](screenshots/admin_users_light.png#only-light){.shot}
![管理用户 — 深色](screenshots/admin_users_dark.png#only-dark){.shot}

**对话浏览器**

![管理对话 — 浅色](screenshots/admin_conversations_light.png#only-light){.shot}
![管理对话 — 深色](screenshots/admin_conversations_dark.png#only-dark){.shot}

**消息质量与评分**

![管理评分 — 浅色](screenshots/admin_ratings_light.png#only-light){.shot}
![管理评分 — 深色](screenshots/admin_ratings_dark.png#only-dark){.shot}

**Stripe 事件日志**

![Stripe 事件 — 浅色](screenshots/admin_stripe_events_light.png#only-light){.shot}
![Stripe 事件 — 深色](screenshots/admin_stripe_events_dark.png#only-dark){.shot}

**系统健康**

![系统健康 — 浅色](screenshots/admin_system_light.png#only-light){.shot}
![系统健康 — 深色](screenshots/admin_system_dark.png#only-dark){.shot}

## 后台任务与编排

在交互式向导中选择 Prefect 作为任务队列，项目会自带一个自托管的 Prefect 服务器和 runner,并为 RAG 同步、账单/邮件提醒和额度维护提供定时流程。

![Prefect dashboard](screenshots/prefect_dashboard.png){.shot}

![Prefect flow runs](screenshots/prefect_runs.png){.shot}

![Prefect task timeline](screenshots/prefect_task_timeline.png){.shot}
