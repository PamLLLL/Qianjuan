---
paths:
  - "app/templates/**/*.html"
---

# Jinja2 + HTMX 前端规范

- 所有页面继承 `base.html`：`{% extends "base.html" %}`
- 使用 `{% block content %}` 填充主内容
- TailwindCSS 通过 CDN 引入，不本地编译
- HTMX 交互用 `hx-post`, `hx-get`, `hx-target`, `hx-swap` 等属性
- SSE 流式接收用 `hx-ext="sse"` 或自定义 JS（static/js/sse.js）
- 组件模板放 `templates/components/`，用 `{% include %}` 引入
- 表单提交用 HTMX 而非传统 form action
- 中文界面，按钮和标签用中文
