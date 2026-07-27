---
paths:
  - "app/api/**/*.py"
---

# FastAPI 路由规范

- 每个模块创建 `router = APIRouter(prefix="/api/xxx", tags=["xxx"])`
- 数据库 session 通过 `Depends(get_session)` 注入
- 请求体用 Pydantic schema，不接受裸 dict
- 响应用 `response_model=XxxResponse`
- SSE 流式响应用 `EventSourceResponse` from sse_starlette
- 分页参数：`page: int = Query(1, ge=1)`, `size: int = Query(20, ge=1, le=100)`
- 路径参数 id 类型用 `uuid.UUID`
- 错误响应统一用 `raise HTTPException(status_code=4xx, detail="...")`
