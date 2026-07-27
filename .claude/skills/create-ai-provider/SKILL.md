---
name: create-ai-provider
description: 新增一个 AI 模型提供商（继承 AiProvider 基类，注册到 registry）
---

## 步骤

1. 在 `app/core/ai/` 下创建 `{provider_name}.py`
   - 继承 `AiProvider` 抽象基类
   - 实现 `generate()` 和 `stream_generate()` 方法
   - 在 `__init__` 中从 config 读取 API Key

2. 在 `app/core/ai/registry.py` 中注册
   - 添加 provider name → class 映射
   - `get_provider(name)` 能正确返回实例

3. 在 `app/config.py` 中添加对应的 API Key 环境变量

4. 在 `.env.example` 中添加 Key 模板

5. 在 `tests/` 中验证 provider 能正确注册和调用（用 mock）
