# AgentScope 2 集成研究：从 Python Agent 模板到多 Agent、多知识库和多租户平台

> 研究基线：`framework-agent-python@b57dece92bf5ca3fc8f17722cd9799ca42fb7001`，`agentscope@9edf84602c3af9399808afa448cd222f8fe1f7f9`（AgentScope `2.0.5`）。

## 结论先行

这两个项目不是互相替换的关系。`framework-agent-python` 已经具备一个 SaaS Agent 应用所需的大部分控制面：认证、组织和成员角色、按组织隔离的会话、知识库权限、计费、渠道接入及前后端产品骨架；AgentScope 2 更适合作为执行面，提供 Agent 运行时、事件流、团队创建与通信、消息总线、工作区、权限中间件及可扩展 RAG。

推荐的演进路线是：

1. 先把 AgentScope 加成模板中的第六种可选 AI runtime，并兼容现有单 Agent WebSocket 协议。
2. 再把 AgentScope session、Redis 消息总线和团队能力接进来。
3. 知识库先复用模板现有的数据和权限模型，通过适配器供 AgentScope 查询；不要同时维护两套摄取链路。
4. 最后实现组织级资源授权、长期记忆、分布式工作区和数据库级隔离。

不建议第一步就直接把 AgentScope 的 FastAPI 子应用公开挂载出来。其当前默认身份依赖临时的 `X-User-ID` 请求头，源码明确写明未来才会替换为 JWT；若直接暴露，会绕过模板现有认证边界（[AgentScope deps.py](../../agentscope/src/agentscope/app/deps.py#L26-L48)）。

## 1. `framework-agent-python` 到底是什么

它不是一个简单的单 Agent demo，而是一个会生成完整 FastAPI + Next.js 应用的项目生成器。

### 1.1 生成器层

当前支持 PydanticAI、Pydantic Deep、LangChain、LangGraph 和 DeepAgents 五种框架（[config.py](../fastapi_gen/config.py#L76-L84)）。AI 框架选择会经过下列链路：

- `ProjectConfig` 保存框架、RAG、MCP、subagent、team、tenancy 和 billing 等开关（[config.py](../fastapi_gen/config.py#L252-L380)）。
- 配置被转换成 Cookiecutter 布尔上下文（[config.py](../fastapi_gen/config.py#L798-L835)）。
- Cookiecutter 生成完整应用，并由 post-generation hook 删除未选框架和功能的文件（[post_gen_project.py](../template/hooks/post_gen_project.py#L130-L140)）。
- 生成结果通过多组合集成测试矩阵验证（[test_template_integration.py](../tests/test_template_integration.py#L191-L204)）。

因此，加入 AgentScope 不能只新增一个 `assistant.py`；CLI、配置、Cookiecutter、依赖、清理 hook、运行时分支、文档和生成测试都要一起变化。

### 1.2 运行时层

浏览器通过 WebSocket 进入 `AgentSession`。路由负责认证和连接生命周期，逐轮执行、停止、HITL、历史、知识库和持久化都在 session service 内完成（[agent.py](../template/%7B%7Bcookiecutter.project_slug%7D%7D/backend/app/api/routes/v1/agent.py#L66-L102)，[agent_session.py](../template/%7B%7Bcookiecutter.project_slug%7D%7D/backend/app/services/agent_session.py#L92-L120)）。

一次典型调用包括：

1. 服务端持久化用户消息并确认用户对会话的访问权。
2. 根据会话保存的 active KB IDs 与当前用户可访问 KB 取交集。
3. 组装框架 Agent、MCP、subagent 和运行上下文。
4. 把框架事件翻译成模板统一的 WebSocket 事件。
5. 持久化助手消息、tool call 和 usage，并触发计费。

除 WebSocket 外，渠道调用使用 `AgentInvocationService`，它也包含各框架的分支（[agent_invocation.py](../template/%7B%7Bcookiecutter.project_slug%7D%7D/backend/app/services/agent_invocation.py#L77-L117)）。AgentScope 接入必须同时覆盖这两个入口，否则 Slack/Telegram 与网页行为会不一致。

当前 `agent_session.py` 已经按框架复制了大量执行流程。首轮集成接受这一现状，直接新增 AgentScope 专用分支，不同时重构其他五个 runtime，以缩小回归面。AgentScope 分支仍应使用独立 `AgentScopeEventAdapter` 隔离事件协议，并通过契约测试证明租户、KB、消息和计费行为与现有入口一致；统一 `AgentRuntimeAdapter` 延后到 AgentScope 功能对等且运行稳定后再评估。

### 1.3 已有多租户和知识库能力

模板目前支持 `single`、`multi_org`、`platform` 三种 tenancy mode；后两者要求启用 teams（[config.py](../fastapi_gen/config.py#L203-L208)，[config.py](../fastapi_gen/config.py#L528-L533)）。

已有模型包含：

- Organization 与 owner/admin/member/viewer 角色，以及同一组织内唯一成员关系（[organization.py](../template/%7B%7Bcookiecutter.project_slug%7D%7D/backend/app/db/models/organization.py#L214-L301)）。
- Conversation 同时记录 `user_id`、`organization_id` 和 active KB IDs（[conversation.py](../template/%7B%7Bcookiecutter.project_slug%7D%7D/backend/app/db/models/conversation.py#L233-L267)）。
- Knowledge Base 支持 PERSONAL、ORG、APP 三种 scope，并记录 owner 与 organization（[knowledge_base.py](../template/%7B%7Bcookiecutter.project_slug%7D%7D/backend/app/db/models/knowledge_base.py#L76-L104)）。
- KB 查询把个人、应用和当前组织可访问资源组合起来（[knowledge_base.py repository](../template/%7B%7Bcookiecutter.project_slug%7D%7D/backend/app/repositories/knowledge_base.py#L17-L35)）。
- Agent 调用前再次将会话所选 KB 与可访问 KB 求交集，阻止客户端伪造跨组织 KB ID（[agent_invocation.py](../template/%7B%7Bcookiecutter.project_slug%7D%7D/backend/app/services/agent_invocation.py#L369-L405)）。

这个隔离目前主要由 service/repository 查询条件保证。源码中未发现 PostgreSQL Row-Level Security 策略，因此它不是数据库强制的租户隔离。现有测试覆盖角色矩阵和 KB scope，但部分 tenancy 测试使用 mock repository，不能等价于真实数据库、缓存和向量库的端到端防泄漏验证。

## 2. AgentScope 2 源码结构与能力

AgentScope 2.0.5 要求 Python 3.11+。核心包保持相对精简，FastAPI service、Redis、SQL、workspace、向量数据库、Mem0 和 ReMe 通过 extras 安装（[pyproject.toml](../../agentscope/pyproject.toml#L21-L160)）。

### 2.1 Agent 与事件模型

`Agent` 构造器接受 model、toolkit、middleware、state、permission engine 和 background offloader（[_agent.py](../../agentscope/src/agentscope/agent/_agent.py#L110-L172)），`reply_stream()` 产出强类型事件（[_agent.py](../../agentscope/src/agentscope/agent/_agent.py#L250-L315)）。事件覆盖文本增量、thinking、tool 调用、HITL、interrupt 和 custom event（[_event.py](../../agentscope/src/agentscope/event/_event.py#L26-L67)）。

这与模板现有 WebSocket 协议可以一一适配：

| AgentScope 事件 | 模板事件/动作 |
|---|---|
| `TextEvent` / delta | token/text delta |
| `ToolCallEvent` | tool-call start/args/result |
| `HumanInTheLoopEvent` | ask-user 请求并等待客户端响应 |
| `InterruptEvent` | stopped/error/final 状态 |
| model call end/usage | 模板 usage 与 billing service |
| custom/team event | 新增 team roster、worker status、message 事件 |

这里应建立显式 `AgentScopeEventAdapter`，而不是让 UI 直接依赖 AgentScope 的事件类。这样框架升级不会扩散到前端和持久化层。

### 2.2 Service、Session 与消息总线

`create_app()` 可独立运行，也可以作为 `/agentscope` 子应用挂到现有 FastAPI；它接收 storage、message bus、workspace manager、KB manager、hub、subagent template 和资源访问策略（[_app.py](../../agentscope/src/agentscope/app/_app.py#L77-L123)）。

AgentScope 把调用和事件订阅分离：`POST /chat/` 触发后台运行，事件从 session SSE 流读取（[_chat.py router](../../agentscope/src/agentscope/app/_router/_chat.py#L49-L160)，[_session.py router](../../agentscope/src/agentscope/app/_router/_session.py#L710-L866)）。MessageBus 负责队列、回放、发布订阅和分布式锁，生产环境应使用 Redis，而不是示例中的进程内实现。

模板现有 WebSocket 可以保留为外部协议，并在内部调用 AgentScope ChatService/Agent；不需要迫使前端同时维护 WebSocket 和 SSE 两种协议。

### 2.3 多 Agent 团队

AgentScope 的团队不是静态 prompt 技巧，而是一组持久化工具和运行时约束：

- `TeamCreate` 创建 team record，并把 leader session 绑定到该 team。
- `AgentCreate` 只允许 leader 创建 worker，为 worker 创建 agent/session，套用 subagent template 和 permission，然后通过 inbox/message bus 唤醒。
- `TeamSay` 根据实时 roster 向单个成员或全体成员发消息。
- `AgentInvite` 可把已有 agent 的新 session 借入团队。
- worker 默认只获得 TeamSay；leader 或非团队 Agent 才获得创建、邀请和删除等管理工具（[_toolkit.py](../../agentscope/src/agentscope/app/_service/_toolkit.py#L194-L228)）。

`SubAgentTemplate` 可以定义角色说明、system prompt、context、ReAct、permission、task 以及是否继承 leader 的 model/workspace 等（[_types.py](../../agentscope/src/agentscope/app/_types.py#L83-L132)）。这正是模板中“团队角色模板”的合适落点。

关键限制：AgentScope 当前 session 和 team tools 都按调用时的同一个 `user_id` 读写；它不原生区分“当前操作人”和“组织资源 owner”。ChatService 虽然能通过 ResourceAccessPolicy 运行跨 owner 共享的 Agent/KB，但 session、workspace、消息和新创建的 team 仍属于当前调用人（[_chat.py service](../../agentscope/src/agentscope/app/_service/_chat.py#L495-L528)）。因此要区分两种产品语义：

- **成员自己的执行团队（建议先做）**：传真实用户 ID。组织 Agent/KB 由 org namespace 持有并通过 policy 分享，但每名成员拥有自己的 session、临时 team、消息和 workspace。原生 AgentScope 模型可以支持。
- **组织所有成员共享的持久团队**：在模板完成 JWT/RBAC 校验后，以 `org:{org_uuid}` 服务身份调用 AgentScope，同时单独记录真实 `actor_user_id`。此时 AgentScope 把所有组织成员视为同一 owner，不能再替模板区分 owner/admin/member/viewer；所有变更权限必须在模板入口强制检查。更长期的方案是扩展 AgentScope service/storage API，显式拆分 actor 与 owner。

资源 namespace 建议为：

- 个人 Agent：`user:{user_uuid}`
- 组织 Agent/Team/KB：`org:{org_uuid}`

不能只通过改写一个 `user_id` 同时解决共享和授权。否则，同一组织不同成员会意外得到各自不同的团队，或者为了共享而被 AgentScope 当作同一个可编辑 owner。

### 2.4 知识库与 RAG

AgentScope 同时提供底层 `KnowledgeBase`、应用层 KB manager 和 `RAGMiddleware`。底层知识库支持强制 metadata filter，并明确把它作为多租户的纵深防御：写入时强制覆盖 metadata，检索时始终应用过滤器（[_knowledge.py](../../agentscope/src/agentscope/rag/_knowledge.py#L25-L30)，[_knowledge.py](../../agentscope/src/agentscope/rag/_knowledge.py#L288-L333)）。

示例 service 使用 `CollectionPerKbManager`，每个 KB 一个向量 collection。ChatService 先通过 resource access service 找出可见 KB，再为 Agent 注入 RAG middleware（[_chat.py service](../../agentscope/src/agentscope/app/_service/_chat.py#L582-L634)）。RAG middleware 支持 agentic search tool 或预先注入上下文两种方式（[_rag.py](../../agentscope/src/agentscope/middleware/_rag.py#L456-L520)）。

模板已经有 KB 元数据、scope、摄取状态和检索工具。第一阶段不应再启动一套 AgentScope KB CRUD 和摄取流程。推荐顺序：

1. 把模板现有 `search_knowledge_base` 封装为 AgentScope Tool，快速得到单一数据源的 RAG。
2. 再实现一个 `KnowledgeBaseManagerBase`/RAG adapter，从模板 KB repository 解析权限并连接现有向量 collection。
3. 向量记录同时带 `org_id`、`kb_id`、`document_id`，检索时强制 tenant + KB filter；即使 collection 路由配置错误也不能跨租户返回。
4. 只有迁移完成后，才考虑让 AgentScope manager 成为唯一摄取入口。

### 2.5 长期记忆

AgentScope 可选 Mem0 和 ReMe。Mem0 示例中同一 `user_id` 会跨 session 共享记忆；ReMe 更依赖共享 workspace。接入时必须把记忆空间与当前 TenantContext 绑定：个人空间用 user namespace，组织共享空间用 org namespace，并按 Agent/成员需要再分层。ReMe 的 workspace 不能跨租户共用。

长期记忆应在 KB 集成之后实施，因为它还需要单独解决用户授权、保留期限、导出、删除和“组织成员离开后如何处理记忆”等产品与合规问题。

### 2.6 AgentScope 自身的多租户边界

AgentScope SQL 表在 Agent、Credential、Session、Team 和 KB 上保存并索引 `user_id`；Message 表则以 `(session_id, msg_id)` 为复合主键（[_tables.py](../../agentscope/src/agentscope/app/storage/_sql/_tables.py#L118-L226)，[_tables.py](../../agentscope/src/agentscope/app/storage/_sql/_tables.py#L338-L364)）。访问服务把 owner 的资源和 policy 允许的跨 owner 引用合并。

默认 `DenyAllResourceAccessPolicy` 拒绝跨 owner 访问。抽象 policy 只负责资源引用，不负责组织或成员管理，源码明确要求调用方实现这一层（[_policy.py](../../agentscope/src/agentscope/app/access/_policy.py#L79-L112)）。这是接入模板组织 RBAC 的正确扩展点。

也就是说，AgentScope 提供了 owner 隔离机制和授权接口，但不是开箱即用的组织级 SaaS tenancy。其 SQL schema 同样没有展示数据库 RLS；隔离依赖 owner-scoped service、全局唯一 ID、访问策略和正确的 key/collection namespace。模板仍应是最终身份和组织权限权威。

## 3. 推荐目标架构

```text
Browser / Slack / Telegram
            |
   Template API + WebSocket
   JWT -> TenantContext -> RBAC
            |
   Framework-specific execution branch
            |
      AgentScopeRuntime
      |       |        |
   Agent    Team    EventAdapter
      |       |        |
   Tools/RAG |     template WS events
      |       |
 Template KB repositories
      |
 tenant-filtered vector store

Shared infrastructure:
PostgreSQL (business + execution state), Redis MessageBus/locks,
tenant-scoped workspace, audit/usage/billing
```

职责边界：

| 领域 | 权威系统 | AgentScope 的作用 |
|---|---|---|
| 登录/JWT/IdP | 模板 | 接收服务端解析后的 TenantContext，不读取外部伪造 header |
| Organization/RBAC | 模板 | custom ResourceAccessPolicy 查询模板成员与角色 |
| 产品会话与消息 | 模板 | session 作为执行 checkpoint；事件回投模板持久化 |
| Agent/Team runtime | AgentScope | Agent、worker、roster、inbox、message bus、permission |
| KB 元数据与摄取 | 初期为模板 | AgentScope tool/middleware adapter |
| 向量隔离 | 两层共同保证 | collection namespace + 强制 metadata filter |
| 计费/配额 | 模板 | 从 AgentScope model events 上报 usage |
| 工作区 | AgentScope manager | 每租户/Agent/session 独立路径或远程 workspace |

建议定义统一上下文，所有 runtime、tool 和数据访问都显式接收：

```python
class TenantContext:
    actor_user_id: UUID
    resource_owner: str  # user:{id} 或 org:{id}
    organization_id: UUID | None
    conversation_id: UUID
    role: OrgRole | None
    request_id: str
```

不要只传 `user_id`。`actor_user_id` 表示谁执行了操作，`resource_owner` 表示资源属于哪个隔离域，两者在组织场景中不同。

## 4. 分阶段实施路线

### Phase 0：固定边界与威胁模型

- 定义 TenantContext、ID 映射、审计字段和个人/组织 owner namespace。
- 决定模板 conversation 与 AgentScope session 是 1:1，建议保存显式 mapping，而不是把一个 ID 到处隐式复用。
- 列出所有数据面：SQL、Redis key、消息队列、workspace path、向量 collection/filter、MCP credential、长期记忆。
- 写跨租户负面测试：知道别人的 UUID 也不能读取、订阅、检索、编辑或唤醒其资源。

完成标准：在引入 AgentScope 前，身份、资源 owner、actor 和组织角色的语义没有歧义。

### Phase 1：第六种 runtime，先达到单 Agent 功能对等

生成器修改面：

- `AIFrameworkType.AGENTSCOPE`、CLI prompt 和配置验证。
- `cookiecutter.json` 的 `use_agentscope`。
- post-generation hook 的 AgentScope 文件保留/删除逻辑。
- backend `pyproject.toml` 的 AgentScope 依赖和需要的 extras。
- AgentScope assistant/runtime 文件。
- WebSocket `AgentSession` 和 channel `AgentInvocationService` 的 AgentScope 专用分支；不在首轮迁移其他 runtime。
- 文档、快照和生成矩阵测试。

运行时范围：普通对话、流式文本、tool calls、取消、错误、HITL、历史、usage 和现有 KB search tool。暂不公开 AgentScope service API，也暂不开 teams。

完成标准：选择 AgentScope 生成的项目可安装、启动并通过与其他框架相同的聊天/RAG/渠道契约测试。

### Phase 2：持久化 Session 与分布式执行

- 使用 SQL/Redis storage 保存 AgentScope execution state。
- 生产环境启用 Redis MessageBus、事件 replay 和分布式 session lock。
- 建立 conversation-session mapping 和幂等 request/turn ID。
- 模板消息仍是产品记录的唯一权威；AgentScope state 是可恢复的执行状态。
- 对“AgentScope 已完成但模板消息写入失败”等双写场景增加 outbox/reconciliation。

完成标准：多进程部署、重连和进程崩溃后不会重复执行一轮，也不会丢失最终消息或计费记录。

### Phase 3：组织级多 Agent 团队

- 配置团队角色的 `SubAgentTemplate`，初始建议仅开放研究员、执行员、审阅员三类受控角色。
- 第一版采用“成员自己的执行团队”：session/team/workspace 属于真实用户，组织 Agent/KB 由 org namespace 持有并经 policy 分享。
- 实现 template-backed `OrganizationResourceAccessPolicy`：把 owner/admin/member/viewer 映射为跨 owner 的 AgentScope read/edit 权限。
- 若后续要求组织共享一个持久 team，新增受保护的 org service-principal 执行路径，并在模板层对每次 team 变更重新校验 actor role；不要直接复用普通 AgentScope router。
- 前端增加 roster、worker state、任务分派、TeamSay 消息、取消和 HITL 投影；外部协议仍走模板 WebSocket。
- MCP credential 与 tool permission 按 worker 最小权限发放，不能因为 leader 可用就自动让所有 worker 可用。
- 每个 Execution Team 最多同时存在 6 个 worker；Tenant 管理员可以调低但不能突破平台上限。团队仍需限制并发、递归深度、token/tool budget，并接入现有 billing/quotas。

完成标准：同组织授权成员可协作，不同组织即使知道 agent/team/session ID 也无法看到事件、消息、workspace 或 tool credential。

### Phase 4：原生 KB/RAG adapter

- 实现 AgentScope KB manager 或 RAG middleware adapter，复用模板 KB repository 和摄取状态。
- 将 personal/org/app scope 映射到 resource owner 与 ResourceAccessPolicy。
- collection routing 与 metadata filter 双重隔离。
- 文档删除、KB 删除和组织删除要同步清理向量、缓存及 AgentScope resource record。
- 对 attachment、agentic RAG、引用来源和重排进行行为契约测试。

完成标准：只有一条摄取链路、一个 KB 元数据权威，且 SQL 权限测试与真实向量检索测试都能证明隔离。

### Phase 5：长期记忆与远程工作区

- Mem0 key 加 resource owner、agent 和可选 member 维度。
- ReMe/workspace 采用 tenant-scoped root；生产环境使用隔离的 Docker/Kubernetes workspace manager。
- 增加记忆查看、删除、保留期限和成员退出策略。
- workspace file、skill、MCP credential 和代码执行遵循同一 access policy。

完成标准：跨 session 有用、跨 tenant 不可见，且用户能解释和删除系统保存的长期记忆。

## 5. 关键接口建议

### 5.1 Runtime adapter（首轮暂缓）

```python
class AgentRuntimeAdapter(Protocol):
    async def stream(
        self,
        *,
        tenant: TenantContext,
        message: str,
        history: list[Message],
        kb_handles: list[KnowledgeBaseHandle],
        cancellation: CancellationToken,
    ) -> AsyncIterator[RuntimeEvent]: ...
```

首轮不会为了 AgentScope 改造全部现有 runtime；上述接口作为后续去重方向保留。当前 AgentScope 专用分支同样不得自行决定组织、KB 和 conversation 权限，只能使用上游已解析的 handle，并让 tool 再做 server-side tenant 校验。

### 5.2 Organization resource policy

```python
class OrganizationResourceAccessPolicy(ResourceAccessPolicyBase):
    async def list_accessible(self, viewer_id, kind, storage): ...
    async def can_edit(
        self, viewer_id, kind, owner_id, resource_id, storage
    ): ...
```

建议映射：owner/admin 可编辑组织 Agent/Team/KB；member 默认可读和运行，但不能改 credential/共享 Agent 配置；viewer 只读，是否能发起运行由产品策略单独决定。个人资源始终只对本人开放，除非用户显式分享。

### 5.3 KB adapter

Adapter 输出不可伪造的 `KnowledgeBaseHandle`，其中包含内部 collection name 和强制 metadata filter；客户端只提交公开 KB UUID，不能提交 collection 名或任意 filter。

## 6. 高风险点

1. **身份混淆**：把 AgentScope `user_id` 同时当 actor 和 organization owner，会破坏组织共享或审计。
2. **直接暴露临时 header auth**：`X-User-ID` 可伪造，必须由模板 JWT server-side 注入。
3. **双套消息权威**：模板 conversation 与 AgentScope message 都作为产品记录会产生删除、编辑、重放和计费不一致。
4. **双套 KB 摄取**：同一文件进入两套 collection 后，删除和权限变更很容易只作用于一边。
5. **仅靠 UI 隔离**：team/session/KB API、SSE/WS 订阅、Redis key、workspace 和向量检索都必须独立校验 owner。
6. **共享 workspace**：尤其是 ReMe、skills 和代码执行，路径配置错误会直接泄露其他租户文件。
7. **无限团队扇出**：worker 可并行唤醒，必须有并发、深度、工具和预算限制。
8. **复制第六份 session 流程**：短期快，长期会让修复和安全检查只落在部分框架；应抽 runtime seam。

## 7. 必须补充的测试

- 生成器：AgentScope × RAG × teams × PostgreSQL/Redis 的最小有效矩阵，以及不支持组合的 validation。
- Runtime contract：每个 adapter 对 text/tool/HITL/error/cancel/usage 的统一事件契约。
- SQL 隔离：真实数据库中两个 org 使用相同公开资源名和已知 UUID 的负面测试。
- 事件隔离：用户不能订阅其他 tenant session SSE/WS 或收到其 TeamSay。
- Redis 隔离：queue、lock、replay buffer 的 key 不能碰撞。
- 向量隔离：故意错误指定 KB ID/filter 时仍不得返回另一 org chunk。
- Workspace 隔离：相对路径、软链接、共享 skill 和 agent worker 场景。
- 权限：owner/admin/member/viewer 对 agent/team/KB/credential 的读、运行、编辑、删除矩阵。
- 故障恢复：worker 崩溃、Redis 重连、双写中断、重复 request id、客户端重连。
- 资源生命周期：组织/成员/KB/Agent/Team 删除后的 SQL、向量、workspace、memory 清理。

## 8. 建议的第一个可交付切片

第一轮实现应严格限制在以下范围：

- CLI 可以选择 AgentScope。
- 生成的项目能用 AgentScope 完成单 Agent 流式聊天。
- 支持现有 KB search tool、HITL、取消、消息持久化和 usage。
- AgentScope 只在内部运行，不公开其原生 `/chat` 与 `/sessions/.../stream`。
- 新增 runtime contract tests 和两租户 KB 负面测试。

这一步完成后再打开 team 能力。这样可以先验证事件协议、会话生命周期、计费与权限边界，避免在基础调用链未稳定时同时引入消息总线、worker session 和共享 workspace。

## 9. 关于“Agile School”的假设

两个仓库和源码中均未出现名为 “Agile School” 的组件。结合上下文，本报告暂按语音/输入误差，将其理解为 **AgentScope 2**，其中“团队、多 Agent、知识库、多租户”都对应 AgentScope 2 的现有能力。如果这里实际指另一个独立项目，需要补充其仓库地址后再做第三方能力映射。
