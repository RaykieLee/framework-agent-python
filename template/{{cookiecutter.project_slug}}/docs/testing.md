 # 测试指南
 
 ## 运行测试

```bash
cd backend

 # 运行所有测试
 pytest
 
 # 带覆盖率运行
 pytest --cov=app --cov-report=term-missing
 
 # 运行特定测试文件
 pytest tests/api/test_health.py -v
 
 # 运行特定测试
 pytest tests/api/test_health.py::test_health_check -v
 
 # 仅运行单元测试
 pytest tests/unit/
 
 # 仅运行集成测试
 pytest tests/integration/
 
 # 带详细输出运行
 pytest -v
 
 # 首个失败后停止
 pytest -x
```

 ## 测试结构

```
tests/
├── conftest.py          # Shared fixtures
├── api/                 # API endpoint tests
│   ├── test_health.py
│   └── test_auth.py
├── unit/                # Unit tests (services, utils)
│   └── test_services.py
└── integration/         # Integration tests
    └── test_db.py
```

 ## 关键夹具（`conftest.py`）

```python
 # 测试用数据库会话
 @pytest.fixture
 async def db_session():
     async with async_session() as session:
         yield session
         await session.rollback()

 # 测试客户端
 @pytest.fixture
 def client():
     return TestClient(app)

 # 已认证客户端
 @pytest.fixture
 async def auth_client(client, test_user):
     token = create_access_token(test_user.id)
     client.headers["Authorization"] = f"Bearer {token}"
     return client
```

 ## 编写测试

 ### API 端点测试
```python
def test_health_check(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
```

 ### 服务层测试
```python
async def test_create_item(db_session):
    service = ItemService(db_session)
    item = await service.create(ItemCreate(name="Test"))
    assert item.name == "Test"
```

 ### 带认证的测试
```python
def test_protected_endpoint(auth_client):
    response = auth_client.get("/api/v1/users/me")
    assert response.status_code == 200
```
{%- if cookiecutter.use_frontend %}

 ## 前端测试

```bash
cd frontend

 # 运行单元测试
 bun test
 
 # 带监听模式运行
 bun test --watch
 
 # 运行 E2E 测试
 bun test:e2e
 
 # 在有头模式下运行 E2E（查看浏览器）
 bun test:e2e --headed
```
{%- endif %}

 ## 测试数据库
 
 测试不会连接真实数据库。`tests/conftest.py` 中的 `client` 夹具通过 FastAPI 的
 `app.dependency_overrides` 使用模拟的异步会话（`AsyncMock`）覆盖
 `get_db_session`，因此测试套件运行快速，无需 PostgreSQL 容器：
 
 - `mock_db_session` — 一个替代 `AsyncSession` 的 `AsyncMock`（`execute`、`commit`、`rollback`、`close`）
 - 覆盖在每个测试前注册，测试后清除
 - 对模拟的调用进行断言，或为被测路径设置 `execute(...)` 的返回值
 
 对于需要执行真实 SQL 的测试，在测试内部实例化你自己的异步引擎/会话，
 而不是依赖共享夹具。
