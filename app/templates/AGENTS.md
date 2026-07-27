# 前端模板约定

- 模板引擎：Jinja2
- CSS 框架：TailwindCSS（CDN 引入）
- 交互库：HTMX（CDN 引入）
- 所有页面继承 base.html
- 组件模板放 components/ 子目录，用 {% include %} 引入
- SSE 流式显示用 static/js/sse.js
- 界面语言：中文
- 按钮、标签、提示文案均用中文
