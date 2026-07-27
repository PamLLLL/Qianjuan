---
paths:
  - "tests/**/*.py"
---

# 测试编写规范

- 框架：pytest + pytest-asyncio
- 数据库：内存 SQLite（`sqlite+aiosqlite://`），每个测试独立 session
- AI Mock：使用 `tests/mocks/mock_provider.py` 的 MockAiProvider
- HTTP 测试：httpx.AsyncClient + FastAPI TestClient
- 测试文件命名：`test_{module}.py`
- 测试函数命名：`test_{action}_{scenario}`，如 `test_create_project_success`
- fixture 放 `conftest.py`：db_session, client, mock_provider
- 异步测试用 `async def test_xxx`（asyncio_mode = "auto"）
- 每个测试独立，不依赖执行顺序
