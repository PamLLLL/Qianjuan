# 后端应用约定

- 框架：FastAPI（异步）
- ORM：SQLAlchemy 2.0 async
- 数据库：SQLite via aiosqlite
- 分层架构：api（路由）→ services（业务）→ models（数据）
- API 层只做参数校验和响应组装，业务逻辑在 services 层
- 所有数据库操作用 async/await
- 配置通过 pydantic-settings 从环境变量读取
