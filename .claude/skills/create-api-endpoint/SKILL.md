---
name: create-api-endpoint
description: 创建新的 FastAPI API 端点（含路由、服务层、schema、测试）
---

## 步骤

1. 在 `app/api/{module}.py` 中添加路由函数
   - 使用 `router = APIRouter(prefix="/api/xxx", tags=["xxx"])`
   - 注入 `session: AsyncSession = Depends(get_session)`
   - 请求体用 Pydantic schema
   - 响应设置 `response_model`

2. 在 `app/services/{module}_service.py` 中实现业务逻辑
   - 函数接收 session 参数
   - 返回 ORM 模型实例

3. 在 `app/main.py` 中注册路由：`app.include_router(xxx.router)`

4. 在 `tests/test_api/test_{module}.py` 中编写测试
   - 用 httpx AsyncClient
   - 测试成功和失败场景

5. 运行 `pytest tests/test_api/test_{module}.py` 验证
