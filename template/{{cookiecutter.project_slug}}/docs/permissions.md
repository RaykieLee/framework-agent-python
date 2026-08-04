{%- if cookiecutter.use_jwt %}
# 权限与访问控制

## 角色

在 `app/db/models/user.py` 中定义了两个角色：

- **admin** — 完全访问所有功能。可以管理用户、RAG 集合、同步源、Webhook 和导出数据。
- **user** — 标准访问权限。可以与 AI Agent 聊天、管理个人资料、查看自己的对话、上传文件到聊天和搜索知识库。

管理员隐式拥有所有用户权限。如果用户是管理员，`User.has_role()` 方法对任何角色返回 `True`。

## 依赖别名

这些在 `app/api/deps.py` 中定义，并在整个路由层中使用：

| 别名 | 解析为 | 访问级别 |
|-------|------------|--------------|
| `CurrentUser` | `Depends(get_current_user)` | 任何已认证用户 |
| `CurrentAdmin` | `Depends(RoleChecker(UserRole.ADMIN))` | 需要管理员角色 |
| `CurrentSuperuser` | `Depends(get_current_active_superuser)` | 需要管理员角色（旧别名）|

## 端点访问矩阵

### 认证

| 端点 | 方法 | 管理员 | 用户 | 未认证 | 备注 |
|----------|--------|-------|------|-----------------|-------|
| `/auth/login` | POST | Y | Y | Y | 返回 JWT 令牌 |
| `/auth/register` | POST | Y | Y | Y | 创建新用户账户 |
| `/auth/refresh` | POST | Y | Y | -- | 需要有效的刷新令牌 |

### 用户

| 端点 | 方法 | 管理员 | 用户 | 备注 |
|----------|--------|-------|------|-------|
| `/users/me` | GET | Y | Y | 自己的个人资料 |
| `/users/me` | PATCH | Y | Y | 自己的个人资料；非管理员不能更改角色 |
| `/users/me/avatar` | POST | Y | Y | 上传自己的头像 |
| `/users/avatar/{user_id}` | GET | Y | Y | 公开头像访问 |
| `/users` | GET | Y | -- | 列出所有用户（仅管理员）|
| `/users/{id}` | GET | Y | -- | 查看任何用户（仅管理员）|
| `/users/{id}` | PATCH | Y | -- | 更新任何用户包括角色（仅管理员）|
| `/users/{id}` | DELETE | Y | -- | 删除任何用户（仅管理员）|

### AI Agent

| 端点 | 方法 | 管理员 | 用户 | 备注 |
|----------|--------|-------|------|-------|
| `/agent/ws/agent` | WS | Y | Y | 与 AI Agent 的 WebSocket 聊天 |

### 对话

| 端点 | 方法 | 管理员 | 用户 | 备注 |
|----------|--------|-------|------|-------|
| `/conversations` | GET | Y | Y | Own conversations only (filtered by user_id) |
| `/conversations` | POST | Y | Y | Create new conversation |
| `/conversations/{id}` | GET | Y | Y | Own conversations only (IDOR protection) |
| `/conversations/{id}` | PATCH | Y | Y | Update title / archived status |
| `/conversations/{id}` | DELETE | Y | Y | Delete own conversation |
| `/conversations/{id}/archive` | POST | Y | Y | Archive own conversation |
| `/conversations/{id}/messages` | GET | Y | Y | List messages in own conversation |
| `/conversations/{id}/messages` | POST | Y | Y | Add message to own conversation |
| `/conversations/export` | GET | Y | -- | Export all conversations (admin only) |

### 消息评分

| 端点 | 方法 | 管理员 | 用户 | 备注 |
|----------|--------|-------|------|-------|
| `/conversations/{id}/messages/{msg_id}/rate` | POST | Y | Y | Rate/update a message (like/dislike) |
| `/conversations/{id}/messages/{msg_id}/rate` | DELETE | Y | Y | Remove own rating |
| `/admin/ratings` | GET | Y | -- | List all ratings with filters (admin only) |
| `/admin/ratings/summary` | GET | Y | -- | Aggregated statistics (admin only) |
| `/admin/ratings/export` | GET | Y | -- | Export ratings JSON/CSV (admin only) |
| `/admin/conversations` | GET | Y | -- | List all conversations (admin only) |

### 文件

| 端点 | 方法 | 管理员 | 用户 | 备注 |
|----------|--------|-------|------|-------|
| `/files/upload` | POST | Y | Y | Upload file for chat |
| `/files/{id}` | GET | Y | Y | Download own files only (ownership check) |
| `/files/{id}/info` | GET | Y | Y | File metadata for own files only |

{%- if cookiecutter.enable_rag %}

### RAG（知识库）

| 端点 | 方法 | 管理员 | 用户 | 备注 |
|----------|--------|-------|------|-------|
| `/rag/supported-formats` | GET | Y | Y | List supported file formats |
| `/rag/search` | POST | Y | Y | Search knowledge base (all users) |
| `/rag/collections` | GET | Y | -- | List collections (admin only) |
| `/rag/collections/{name}` | POST | Y | -- | Create collection (admin only) |
| `/rag/collections/{name}` | DELETE | Y | -- | Drop collection (admin only) |
| `/rag/collections/{name}/info` | GET | Y | -- | Collection stats (admin only) |
| `/rag/collections/{name}/documents` | GET | Y | -- | List documents in collection (admin only) |
| `/rag/collections/{name}/documents/{id}` | DELETE | Y | -- | Delete document (admin only) |
| `/rag/collections/{name}/ingest` | POST | Y | -- | Upload and ingest file (admin only) |
| `/rag/documents` | GET | Y | -- | List tracked RAG documents (admin only) |
| `/rag/documents/{id}/download` | GET | Y | -- | Download original file (admin only) |
| `/rag/documents/{id}` | DELETE | Y | -- | Delete tracked document (admin only) |
| `/rag/documents/{id}/retry` | POST | Y | -- | Retry failed ingestion (admin only) |
| `/rag/sync/logs` | GET | Y | -- | List sync logs (admin only) |
| `/rag/sync/local` | POST | Y | -- | Trigger local directory sync (admin only) |
| `/rag/sync/{id}` | DELETE | Y | -- | Cancel sync operation (admin only) |
| `/rag/sync/sources` | GET | Y | -- | List sync sources (admin only) |
| `/rag/sync/sources` | POST | Y | -- | Create sync source (admin only) |
| `/rag/sync/sources/{id}` | PATCH | Y | -- | Update sync source (admin only) |
| `/rag/sync/sources/{id}` | DELETE | Y | -- | Delete sync source (admin only) |
| `/rag/sync/sources/{id}/trigger` | POST | Y | -- | Trigger manual sync (admin only) |
| `/rag/sync/connectors` | GET | Y | -- | List available connector types (admin only) |
{%- endif %}

{%- if cookiecutter.enable_webhooks and cookiecutter.use_database %}

### Webhook

| 端点 | 方法 | 管理员 | 用户 | 备注 |
|----------|--------|-------|------|-------|
| `/webhooks` | GET | Y | -- | List webhooks (admin only) |
| `/webhooks` | POST | Y | -- | Create webhook (admin only) |
| `/webhooks/{id}` | GET | Y | -- | Get webhook details |
| `/webhooks/{id}` | PATCH | Y | -- | Update webhook |
| `/webhooks/{id}` | DELETE | Y | -- | Delete webhook |
| `/webhooks/{id}/test` | POST | Y | -- | Send test event |
| `/webhooks/{id}/regenerate-secret` | POST | Y | -- | Regenerate webhook secret |
| `/webhooks/{id}/deliveries` | GET | Y | -- | Delivery history |
{%- endif %}

### 健康检查

| 端点 | 方法 | 管理员 | 用户 | 未认证 | 备注 |
|----------|--------|-------|------|-----------------|-------|
| `/health` | GET | Y | Y | Y | No auth required |

## 工作原理

### JWT 流程

1. User sends credentials to `POST /auth/login`.
2. Server validates credentials, returns `access_token` + `refresh_token`.
3. Client includes `Authorization: Bearer <access_token>` on subsequent requests.
4. `get_current_user` dependency extracts the JWT, verifies it, loads the user.
5. If the token is expired, the client uses `POST /auth/refresh` to get a new one.

### 角色检查

`RoleChecker` is a callable class that wraps `get_current_user`:

```python
class RoleChecker:
    def __init__(self, required_role: UserRole):
        self.required_role = required_role

    async def __call__(self, user = Depends(get_current_user)) -> User:
        if not user.has_role(self.required_role):
            raise AuthorizationError(...)
        return user
```

`User.has_role()` returns `True` if:
- The user's role matches the required role, OR
- The user is an admin (admin has all permissions).

### IDOR 防护

Resources owned by users (conversations, files) are protected at the service
layer. The service receives the current user's ID from the route and uses it
to filter queries:

```python
# In conversation route
items, total = await service.list_conversations(user_id=current_user.id, ...)

# In file route
chat_file = await file_upload_svc.get_user_file(file_id, current_user.id)
# Raises NotFoundError if user_id doesn't match
```

{%- if cookiecutter.enable_rag %}

### RAG 访问模型

RAG operates on a **global** access model:

- **Search** is available to all authenticated users (`CurrentUser`). All users
  search the same collections and see the same results.
- **Management** (create/delete collections, upload documents, configure sync
  sources) requires admin access (`CurrentAdmin`).
- There is no per-user document isolation. If you need per-user collections,
  you would need to extend the service layer to scope collections by user.
{%- endif %}

{%- if cookiecutter.use_api_key %}

### API 密钥认证

For programmatic access, clients can authenticate via API key:

```
X-API-Key: your-api-key-here
```

The `verify_api_key` dependency validates the key using constant-time comparison.
API key auth grants full access (no role distinction). Use it for trusted
server-to-server communication.
{%- endif %}

## 创建用户

### 通过 CLI

```bash
# Create a regular user
uv run {{ cookiecutter.project_slug }} user create --email user@example.com --password secret

# Create an admin user
uv run {{ cookiecutter.project_slug }} user create-admin --email admin@example.com --password secret

# Change user role
uv run {{ cookiecutter.project_slug }} user set-role user@example.com --role admin
```

### 通过 Make

```bash
make create-admin    # Interactive admin creation
make user-create     # Interactive user creation
make user-list       # List all users
```

### 通过快速开始

```bash
make quickstart      # Creates admin@example.com / admin123 automatically
```

{%- else %}
# 权限与访问控制

This project was generated without JWT authentication. All endpoints are
publicly accessible. To add authentication, regenerate the project with
the `--auth jwt` option.
{%- endif %}
