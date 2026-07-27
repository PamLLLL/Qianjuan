# 测试约定

- 框架：pytest + pytest-asyncio（asyncio_mode = "auto"）
- 数据库：内存 SQLite（每个测试函数独立 session）
- AI Mock：`tests/mocks/mock_provider.py`，返回预设 JSON
- HTTP 测试：httpx.AsyncClient + FastAPI app
- fixture 集中在 `conftest.py`：db_session, client, mock_provider
- 测试文件命名：`test_{module}.py`
- 测试函数命名：`test_{action}_{scenario}`
- 按模块分目录：test_models/, test_schemas/, test_services/, test_api/, test_rules_engine/
