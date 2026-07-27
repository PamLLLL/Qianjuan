# AI 提供商约定

- 所有 provider 继承 `AiProvider` 抽象基类
- 必须实现 `generate()` 和 `stream_generate()` 两个方法
- generate() 返回完整字符串
- stream_generate() 返回 AsyncGenerator[str, None]
- 重试逻辑在基类 `_call_with_retry()` 中统一处理
- API Key 从 app.config 读取（不硬编码）
- 通过 `registry.py` 注册和获取 provider 实例
- provider name 使用小写：claude, openai, deepseek, qwen
