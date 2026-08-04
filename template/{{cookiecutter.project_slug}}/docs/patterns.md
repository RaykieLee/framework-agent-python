# 代码模式

## 依赖注入

使用 FastAPI 的 `Depends()` 进行依赖注入：

```python
from app.api.deps import get_db, get_current_user

@router.get("/conversations")
async def list_conversations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = ConversationService(db)
    return await service.get_by_user(current_user.id)
```

> **重要：** 路由层绝不包含直接数据库调用。所有数据访问都经过服务层，服务层再委托给仓库层。

`app/api/deps.py` 中可用的依赖：
- `get_db` — 数据库会话
- `get_current_user` — 已认证用户（未认证时抛出 401）
- `get_current_user_optional` — 用户或 None
{%- if cookiecutter.enable_redis %}
- `get_redis` — Redis 连接
{%- endif %}

## 服务层模式

每个功能使用相同的模式：服务类接收 DB 会话，实例化其仓库，并提供业务级方法。服务层是**唯一**抛出领域异常的层。

```python
class ConversationService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = ConversationRepository()

    async def create(self, data: ConversationCreate, user_id: UUID) -> Conversation:
        # Business validation
        return await self.repo.create(self.db, user_id=user_id, **data.model_dump())

    async def get_or_raise(self, id: UUID) -> Conversation:
        conv = await self.repo.get_by_id(self.db, id)
        if not conv:
            raise NotFoundError(message="Conversation not found", details={"id": str(id)})
        return conv
```

All current services follow this pattern: `UserService`, `ConversationService`,
`FileUploadService`, `FileStorageService`
{%- if cookiecutter.enable_rag %}, `RagDocumentService`, `RagSyncService`, `SyncSourceService`
{%- endif %}.

## 仓库层模式

仓库层仅处理数据访问。它们**不包含**业务逻辑，始终使用 `flush()` 而非 `commit()`，以便调用者控制事务：

```python
class ConversationRepository:
    async def get_by_id(self, db: AsyncSession, id: UUID) -> Conversation | None:
        return await db.get(Conversation, id)

    async def create(self, db: AsyncSession, **kwargs) -> Conversation:
        conv = Conversation(**kwargs)
        db.add(conv)
        await db.flush()  # Not commit! Let dependency manage transaction
        await db.refresh(conv)
        return conv

    async def get_by_user(
        self, db: AsyncSession, user_id: UUID, skip: int = 0, limit: int = 100
    ) -> list[Conversation]:
        result = await db.execute(
            select(Conversation)
            .where(Conversation.user_id == user_id)
            .offset(skip).limit(limit)
        )
        return list(result.scalars().all())
```

## 异常处理

在服务层中使用领域异常：

```python
from app.core.exceptions import NotFoundError, AlreadyExistsError, ValidationError

# In service
if not conversation:
    raise NotFoundError(
        message="Conversation not found",
        details={"id": str(id)}
    )

if await self.repo.exists_by_email(self.db, email):
    raise AlreadyExistsError(
        message="User with this email already exists"
    )
```

异常处理器自动转换为 HTTP 响应。

## 模式模式

为不同操作分离模式：

```python
# 包含共享字段的基础类
class UserBase(BaseModel):
    email: str
    full_name: str | None = None

# 用于创建（输入）
class UserCreate(UserBase):
    password: str

# 用于更新（全部可选）
class UserUpdate(BaseModel):
    full_name: str | None = None
    email: str | None = None

# 用于响应（包含数据库字段）
class UserResponse(UserBase):
    id: UUID
    created_at: datetime
    updated_at: datetime | None

    model_config = ConfigDict(from_attributes=True)
```
{%- if cookiecutter.enable_rag %}

## 连接器模式（RAG 同步）

远程文档源（Google Drive、S3 等）使用 `app/services/rag/connectors/` 中定义的可插拔连接器模式。每个连接器继承自 `BaseSyncConnector`，并在 `CONNECTOR_REGISTRY` 字典中注册。

### 添加新连接器

1. 在 `app/services/rag/connectors/` 中创建文件（例如 `sharepoint.py`）。
2. 继承 `BaseSyncConnector` 并实现所需方法。
3. 在 `CONNECTOR_REGISTRY` 中注册连接器。

```python
from app.services.rag.connectors import BaseSyncConnector, RemoteFile, CONNECTOR_REGISTRY

class SharePointConnector(BaseSyncConnector):
    CONNECTOR_TYPE = "sharepoint"
    DISPLAY_NAME = "SharePoint"
    CONFIG_SCHEMA = {
        "site_url": {"label": "Site URL", "required": True},
        "client_id": {"label": "Client ID", "required": True},
    }

    async def list_files(self, config: dict) -> list[RemoteFile]:
        # Return metadata for available files
        ...

    async def download_file(self, file: RemoteFile, dest_dir: Path) -> Path:
        # Download file to dest_dir, return local Path
        ...

# Register so the sync service can discover it
CONNECTOR_REGISTRY["sharepoint"] = SharePointConnector
```

The `RagSyncService` uses `CONNECTOR_REGISTRY` to look up the right connector
by type, validate its config, list remote files, download them, and hand them
off to the ingestion pipeline.
{%- endif %}
{%- if cookiecutter.use_frontend %}

## 前端模式

### 认证（HTTP-only Cookie）

```typescript
import { useAuth } from '@/hooks/use-auth';

function Component() {
    const { user, isAuthenticated, login, logout } = useAuth();
}
```

### 状态管理（Zustand）

```typescript
import { useAuthStore } from '@/stores/auth-store';

const { user, setUser, logout } = useAuthStore();
```

### WebSocket 聊天

```typescript
import { useChat } from '@/hooks/use-chat';

function ChatPage() {
    const { messages, sendMessage, isStreaming } = useChat();
}
```
{%- endif %}
