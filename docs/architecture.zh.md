# 架构

本文档描述由 Full-Stack AI Agent Template 生成的项目的架构。

关于高层系统概览图(前端、后端、AI 智能体、RAG 管线、基础设施),参见 [README](../README.md#-architecture)。

## 后端分层架构

后端遵循清晰的分层架构，关注点分离明确：

```
┌─────────────────────────────────────────────────────────────┐
│                      API Layer (Routes)                      │
│  HTTP endpoints, request validation, response serialization │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     Service Layer                            │
│      Business logic, orchestration, error handling           │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   Repository Layer                           │
│          Data access, database queries, CRUD                 │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      Database                                │
│              PostgreSQL (async, SQLAlchemy 2.0)              │
└─────────────────────────────────────────────────────────────┘
```

---

## 目录结构

```
app/
├── api/                    # API 层
│   ├── routes/
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── health.py
│   │       ├── auth.py
│   │       ├── users.py
│   │       └── items.py
│   ├── deps.py             # 依赖注入
│   ├── router.py           # 路由聚合
│   └── exception_handlers.py
│
├── services/               # 服务层
│   ├── __init__.py
│   ├── user.py
│   └── item.py
│
├── repositories/           # 仓储层
│   ├── __init__.py
│   ├── base.py             # 通用 CRUD 操作
│   ├── user.py
│   └── item.py
│
├── schemas/                # Pydantic 模型
│   ├── __init__.py
│   ├── base.py
│   ├── user.py
│   └── item.py
│
├── db/                     # 数据库
│   ├── models/
│   │   ├── __init__.py
│   │   ├── user.py
│   │   └── item.py
│   ├── base.py
│   └── session.py
│
└── core/                   # 核心配置
    ├── config.py
    ├── security.py
    └── exceptions.py
```

---

## 各层职责

### API 层(`app/api/routes/`)

API 层处理 HTTP 相关事务：

- **请求校验** —— Pydantic schema 校验传入数据
- **认证** —— 依赖项校验 JWT/API 密钥
- **响应序列化** —— 为客户端格式化数据
- **错误响应** —— HTTP 状态码和错误信息

```python
# app/api/routes/v1/items.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_user
from app.schemas.item import ItemCreate, ItemResponse
from app.services.item import ItemService

router = APIRouter(prefix="/items", tags=["items"])


@router.post("/", response_model=ItemResponse)
async def create_item(
    item_in: ItemCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new item."""
    service = ItemService(db)
    item = await service.create(item_in)
    return item
```

**关键原则：**
- 路由保持精简 —— 把业务逻辑委托给服务
- 使用依赖注入来获取数据库会话和认证
- 把请求/响应 schema 与内部模型分开

### 服务层(`app/services/`)

服务层包含业务逻辑和编排：

- **业务规则** —— 超出 schema 约束范围的校验
- **错误处理** —— 领域特定的异常
- **编排** —— 协调多个仓储
- **外部服务** —— API 调用、邮件等

```python
# app/services/item.py
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.db.models.item import Item
from app.repositories import item_repo
from app.schemas.item import ItemCreate, ItemUpdate


class ItemService:
    """Service for item-related business logic."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, item_id: UUID) -> Item:
        """Get item by ID."""
        item = await item_repo.get_by_id(self.db, item_id)
        if not item:
            raise NotFoundError(
                message="Item not found",
                details={"item_id": str(item_id)},
            )
        return item

    async def create(self, item_in: ItemCreate) -> Item:
        """Create a new item."""
        # Business validation could go here
        return await item_repo.create(
            self.db,
            title=item_in.title,
            description=item_in.description,
        )

    async def update(self, item_id: UUID, item_in: ItemUpdate) -> Item:
        """Update an item."""
        item = await self.get_by_id(item_id)
        update_data = item_in.model_dump(exclude_unset=True)
        return await item_repo.update(self.db, db_item=item, update_data=update_data)
```

**关键原则：**
- 服务是无状态的(除了数据库会话)
- 抛出领域异常，而非 HTTP 异常
- 服务可以调用其他服务来完成复杂操作

### 仓储层(`app/repositories/`)

仓储层处理数据访问：

- **CRUD 操作** —— 创建、读取、更新、删除
- **查询构建** —— 复杂的数据库查询
- **数据映射** —— ORM 模型交互

```python
# app/repositories/item.py
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.item import Item


class ItemRepository:
    """Repository for Item database operations."""

    async def get_by_id(self, db: AsyncSession, item_id: UUID) -> Item | None:
        """Get item by ID."""
        return await db.get(Item, item_id)

    async def get_multi(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100,
        active_only: bool = False,
    ) -> list[Item]:
        """Get multiple items with pagination."""
        query = select(Item)
        if active_only:
            query = query.where(Item.is_active == True)
        query = query.offset(skip).limit(limit)
        result = await db.execute(query)
        return list(result.scalars().all())

    async def create(
        self,
        db: AsyncSession,
        *,
        title: str,
        description: str | None = None,
    ) -> Item:
        """Create a new item."""
        item = Item(title=title, description=description)
        db.add(item)
        await db.flush()
        await db.refresh(item)
        return item


# Singleton instance
item_repo = ItemRepository()
```

**关键原则：**
- 仓储是针对特定模型的
- 使用 `db.flush()` 而非 `db.commit()` —— 把事务交给调用方管理
- 返回 ORM 模型，而非字典

---

## 基础仓储

脚手架提供了一个通用的基础仓储，用于常见的 CRUD 操作：

```python
# app/repositories/base.py
from typing import Any, Generic, TypeVar

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import Base

ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class BaseRepository(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """Base class for repository operations."""

    def __init__(self, model: type[ModelType]):
        self.model = model

    async def get(self, db: AsyncSession, id: Any) -> ModelType | None:
        """Get a single record by ID."""
        return await db.get(self.model, id)

    async def get_multi(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[ModelType]:
        """Get multiple records with pagination."""
        result = await db.execute(
            select(self.model).offset(skip).limit(limit)
        )
        return list(result.scalars().all())

    async def create(
        self,
        db: AsyncSession,
        *,
        obj_in: CreateSchemaType,
    ) -> ModelType:
        """Create a new record."""
        obj_in_data = obj_in.model_dump()
        db_obj = self.model(**obj_in_data)
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj
```

---

## Schema(Pydantic 模型)

Schema 定义请求/响应结构：

```python
# app/schemas/item.py
from uuid import UUID
from datetime import datetime

from pydantic import BaseModel, Field


class ItemBase(BaseModel):
    """Shared properties."""
    title: str = Field(..., min_length=1, max_length=100)
    description: str | None = None


class ItemCreate(ItemBase):
    """Properties to receive on creation."""
    pass


class ItemUpdate(BaseModel):
    """Properties to receive on update."""
    title: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = None


class ItemResponse(ItemBase):
    """Properties to return to client."""
    id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
```

**关键原则：**
- 为创建、更新和响应分别使用独立的 schema
- 使用 `from_attributes = True` 做 ORM 模型转换
- 施加校验约束(min_length、max_length 等)

---

## 数据库模型

SQLAlchemy 模型定义数据库 schema:

```python
# app/db/models/item.py
from uuid import uuid4
from datetime import datetime

from sqlalchemy import String, Text, Boolean, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base


class Item(Base):
    """Item model."""

    __tablename__ = "items"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
```

---

## 依赖注入

FastAPI 依赖项提供数据库会话和认证：

```python
# app/api/deps.py
from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_token
from app.db.session import async_session_maker
from app.services.user import UserService

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Get database session."""
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Get current authenticated user."""
    payload = verify_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )

    user_service = UserService(db)
    user = await user_service.get_by_id(payload["sub"])
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    return user


# Type aliases for cleaner route signatures
DB = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated["User", Depends(get_current_user)]
```

在路由中使用：

```python
@router.get("/me")
async def get_me(current_user: CurrentUser):
    return current_user


@router.get("/items")
async def list_items(db: DB):
    service = ItemService(db)
    return await service.get_multi()
```

---

## 异常处理

自定义异常提供一致的错误响应：

```python
# app/core/exceptions.py
from typing import Any


class AppError(Exception):
    """Base application error."""

    def __init__(
        self,
        message: str,
        status_code: int = 500,
        details: dict[str, Any] | None = None,
    ):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class NotFoundError(AppError):
    """Resource not found."""

    def __init__(self, message: str = "Not found", details: dict | None = None):
        super().__init__(message, status_code=404, details=details)


class AlreadyExistsError(AppError):
    """Resource already exists."""

    def __init__(self, message: str = "Already exists", details: dict | None = None):
        super().__init__(message, status_code=409, details=details)


class ValidationError(AppError):
    """Validation failed."""

    def __init__(self, message: str = "Validation error", details: dict | None = None):
        super().__init__(message, status_code=422, details=details)


class UnauthorizedError(AppError):
    """Authentication required."""

    def __init__(self, message: str = "Unauthorized", details: dict | None = None):
        super().__init__(message, status_code=401, details=details)


class ForbiddenError(AppError):
    """Permission denied."""

    def __init__(self, message: str = "Forbidden", details: dict | None = None):
        super().__init__(message, status_code=403, details=details)
```

异常处理器把它们转换为 HTTP 响应：

```python
# app/api/exception_handlers.py
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.exceptions import AppError


def register_exception_handlers(app: FastAPI) -> None:
    """Register custom exception handlers."""

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.message,
                "details": exc.details,
            },
        )
```

---

## 测试

分层架构让测试变得直接：

```python
# tests/test_services.py
import pytest
from unittest.mock import AsyncMock, patch

from app.services.item import ItemService
from app.schemas.item import ItemCreate


@pytest.mark.asyncio
async def test_create_item():
    """Test item creation."""
    mock_db = AsyncMock()

    with patch("app.services.item.item_repo") as mock_repo:
        mock_repo.create.return_value = Item(
            id="123",
            title="Test",
            description="Test item",
        )

        service = ItemService(mock_db)
        item = await service.create(ItemCreate(title="Test", description="Test item"))

        assert item.title == "Test"
        mock_repo.create.assert_called_once()
```

---

## 最佳实践

1. **保持路由精简** —— 委托给服务
2. **服务处理业务逻辑** —— 校验、编排
3. **仓储处理数据** —— 查询、CRUD
4. **使用依赖注入** —— 以提升可测试性
5. **抛出领域异常** —— 不要在服务中抛 HTTP 异常
6. **合理使用事务** —— 仓储中用 `flush()`,依赖项中用 `commit()`
7. **分离 schema** —— 创建、更新、响应各一套
8. **全面类型标注** —— Pydantic + Python 类型提示
