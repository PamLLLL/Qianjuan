# 千卷 QianJuan — AI 小说生成器

## 构建与运行
- `pip install -e ".[dev]"` 安装依赖
- `uvicorn app.main:app --reload` 启动开发服务器（端口 8000）
- `pytest` 运行测试
- `ruff check app/` 代码检查

## 技术栈
- 后端：Python 3.11+ / FastAPI / SQLAlchemy(async) / aiosqlite
- 前端：Jinja2 + HTMX + TailwindCSS（CDN）
- AI：DeepSeek (MVP 首选) / Claude / GPT / 通义千问
- 数据库：SQLite（存储在 data/ 目录）

## 架构概览
- `app/models/` — SQLAlchemy 异步模型（14 张表），全部继承 Base
- `app/schemas/` — Pydantic v2 请求/响应模型
- `app/api/` — FastAPI 路由（7 个模块），统一 /api/ 前缀
- `app/services/` — 业务逻辑层（9 个服务），接收 AsyncSession 参数
- `app/core/ai/` — AI 提供商抽象（AiProvider 基类 → 具体实现）
- `app/core/markdown/` — Markdown frontmatter 解析器
- `app/templates/` — Jinja2 模板 + HTMX 交互
- `rules/` — Markdown 规则文件（平台/生成/风格/类型），运行时注入 Prompt
- `tests/` — pytest + pytest-asyncio，Mock AI Provider，内存 SQLite

## 关键约定
- 所有数据库操作用 async/await + AsyncSession
- AI 调用统一走 AiProvider 抽象基类，内置指数退避重试
- 规则文件格式：YAML frontmatter + Markdown 正文
- API Key 仅存 .env 文件，不入数据库
- SSE 流式响应用 sse-starlette 的 EventSourceResponse
- 前端交互优先用 HTMX (hx-*) 属性，减少手写 JS
- UUID 主键用 uuid4 默认值
- JSON 字段用 SQLAlchemy 的 JSON 类型

## PRD 文档
- @/home/liuy405/novel-generator-PRD.md
