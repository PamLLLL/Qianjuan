# 路由层约定

- 每个模块一个 `APIRouter`，设置 `prefix` 和 `tags`
- 数据库 session 通过 `Depends(get_session)` 注入
- 请求体使用 Pydantic schema（不接受裸 dict）
- 响应设置 `response_model` 参数
- 分页用 `page` + `size` Query 参数
- SSE 流式响应：返回 `EventSourceResponse(generator())`
- 错误用 `HTTPException(status_code=xxx, detail="...")`
- 路由函数名：`{action}_{resource}`，如 `create_project`
- 所有路由在 `app/main.py` 中通过 `app.include_router()` 注册
