# 服务层约定

- 服务函数是独立的 async 函数（不封装成类）
- 函数签名第一个参数是 `session: AsyncSession`
- 不在服务层创建 session，由 API 层注入
- AI 调用通过 `registry.get_provider(name)` 获取 provider
- 规则加载通过 `RulesEngine` 实例
- 返回 ORM 模型实例（不在服务层序列化）
- 抛自定义异常，由 API 层捕获转 HTTPException
