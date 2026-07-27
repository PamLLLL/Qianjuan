# Markdown 规则文件约定

- 格式：YAML frontmatter + Markdown 正文
- frontmatter 必含：name, type, display_name, description, version
- type 取值：platform / generation / style / genre
- 正文用 Markdown 标题和列表组织
- 文件名用英文小写 + 连字符（如 chapter-content.md）
- 平台规则放 platforms/，生成规则放 generation/，风格放 styles/，类型放 genres/
- 运行时由 RulesEngine 读取并注入 AI Prompt
- 修改后立即生效（热更新），无需重启服务
