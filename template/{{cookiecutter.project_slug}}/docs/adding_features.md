 # 添加新功能
 
 ## 添加新的 API 端点
 
 本示例从头到尾添加一个"通知"功能，遵循代码库中使用的
 仓库 + 服务模式。**路由层绝不包含直接数据库调用**——所有数据访问通过服务层，
 服务层再委托给仓库层。
 
 1. **在 `schemas/` 中创建模式**
   ```python
   # schemas/notification.py
   from datetime import datetime
   from uuid import UUID

   from pydantic import BaseModel


   class NotificationCreate(BaseModel):
       title: str
       body: str
       channel: str = "email"


   class NotificationResponse(BaseModel):
       id: UUID
       title: str
       body: str
       channel: str
       is_read: bool
       created_at: datetime
   ```

 2. **在 `db/models/` 中创建模型**
   ```python
   # db/models/notification.py
   from uuid import uuid4

   from sqlalchemy import Boolean, DateTime, String, func
   from sqlalchemy.dialects.postgresql import UUID
   from sqlalchemy.orm import Mapped, mapped_column

   from app.db.base import Base


   class Notification(Base):
       __tablename__ = "notifications"

       id: Mapped[UUID] = mapped_column(
           UUID(as_uuid=True), primary_key=True, default=uuid4
       )
       title: Mapped[str] = mapped_column(String(255))
       body: Mapped[str] = mapped_column(String)
       channel: Mapped[str] = mapped_column(String(50), default="email")
       is_read: Mapped[bool] = mapped_column(Boolean, default=False)
       created_at: Mapped[DateTime] = mapped_column(
           DateTime(timezone=True), server_default=func.now()
       )
   ```

 不要忘记在 `db/models/__init__.py` 中导入它。

 3. **在 `repositories/` 中创建仓库**
   ```python
   # repositories/notification.py
   from uuid import UUID

   from sqlalchemy import select
   from sqlalchemy.ext.asyncio import AsyncSession

   from app.db.models.notification import Notification


   class NotificationRepository:
       async def create(self, db: AsyncSession, **kwargs) -> Notification:
           notification = Notification(**kwargs)
           db.add(notification)
           await db.flush()
           await db.refresh(notification)
           return notification

       async def get_by_id(self, db: AsyncSession, notification_id: UUID) -> Notification | None:
           return await db.get(Notification, notification_id)

       async def list_unread(self, db: AsyncSession, limit: int = 50) -> list[Notification]:
           result = await db.execute(
               select(Notification)
               .where(Notification.is_read.is_(False))
               .order_by(Notification.created_at.desc())
               .limit(limit)
           )
           return list(result.scalars().all())
   ```

 4. **在 `services/` 中创建服务**
   ```python
   # services/notification.py
   from uuid import UUID

   from sqlalchemy.ext.asyncio import AsyncSession

   from app.core.exceptions import NotFoundError
   from app.repositories.notification import NotificationRepository
   from app.schemas.notification import NotificationCreate


   class NotificationService:
       def __init__(self, db: AsyncSession):
           self.db = db
           self.repo = NotificationRepository()

       async def create(self, data: NotificationCreate) -> "Notification":
           return await self.repo.create(self.db, **data.model_dump())

       async def get_or_raise(self, notification_id: UUID) -> "Notification":
           notification = await self.repo.get_by_id(self.db, notification_id)
           if not notification:
               raise NotFoundError(
                   message="Notification not found",
                   details={"id": str(notification_id)},
               )
           return notification

       async def list_unread(self) -> list["Notification"]:
           return await self.repo.list_unread(self.db)
   ```

 5. **在 `api/deps.py` 中注册依赖**
   ```python
   from app.services.notification import NotificationService


   def get_notification_service(db: DBSession) -> NotificationService:
       """Create NotificationService instance with database session."""
       return NotificationService(db)


   NotificationSvc = Annotated[NotificationService, Depends(get_notification_service)]
   ```

 6. **在 `api/routes/v1/` 中创建路由**
   ```python
   # api/routes/v1/notifications.py
   from fastapi import APIRouter, status

   from app.api.deps import CurrentUser, NotificationSvc
   from app.schemas.notification import NotificationCreate, NotificationResponse

   router = APIRouter()


   @router.post("/", response_model=NotificationResponse, status_code=status.HTTP_201_CREATED)
   async def create_notification(
       data: NotificationCreate,
       current_user: CurrentUser,
       service: NotificationSvc,
   ):
       return await service.create(data)


   @router.get("/", response_model=list[NotificationResponse])
   async def list_unread(
       current_user: CurrentUser,
       service: NotificationSvc,
   ):
       return await service.list_unread()
   ```

 7. **在 `api/routes/v1/__init__.py` 中注册路由**
   ```python
   from app.api.routes.v1 import notifications

   v1_router.include_router(
       notifications.router, prefix="/notifications", tags=["notifications"]
   )
   ```

 ## 添加自定义 CLI 命令

 命令从 `app/commands/` 自动发现。

```python
 # app/commands/my_command.py
 from app.commands import command, success, error
 import click
 
 @command("my-command", help="描述该命令的功能")
 @click.option("--name", "-n", required=True, help="名称参数")
 def my_command(name: str):
     # 你的逻辑在这里
     success(f"完成：{name}")
```

 运行：`uv run {{ cookiecutter.project_slug }} cmd my-command --name test`
{%- if cookiecutter.use_pydantic_ai %}

 ## 添加 AI Agent 工具（PydanticAI）

```python
 # app/agents/assistant.py
 @agent.tool
 async def my_tool(ctx: RunContext[Deps], param: str) -> dict:
     """LLM 使用的工具描述——具体说明其功能。"""
     # 通过 ctx.deps 访问依赖
     result = await some_operation(param)
     return {"result": result}
```
{%- endif %}
{%- if cookiecutter.use_langchain %}

 ## 添加 AI Agent 工具（LangChain）

```python
 # app/agents/langchain_assistant.py
 from langchain.tools import tool
 
 @tool
 def my_tool(param: str) -> dict:
     """LLM 使用的工具描述——具体说明其功能。"""
     result = some_operation(param)
     return {"result": result}
```
{%- endif %}

 ## 添加数据库迁移

```bash
 # 创建迁移
 uv run alembic revision --autogenerate -m "添加通知表"
 
 # 应用迁移
 uv run alembic upgrade head
 
 # 或使用 CLI
 uv run {{ cookiecutter.project_slug }} db migrate -m "添加通知表"
 uv run {{ cookiecutter.project_slug }} db upgrade
```
