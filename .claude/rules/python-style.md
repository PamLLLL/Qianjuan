---
paths:
  - "app/**/*.py"
---

# Python 编码规范

- 使用 `from __future__ import annotations` 支持延迟类型解析
- 类型注解：函数参数和返回值必须标注类型
- 字符串用双引号
- f-string 优先于 .format() 和 %
- 异步函数用 `async def`，异步上下文用 `async with`
- 避免裸 except，至少 `except Exception`
- dataclass/Pydantic model 优先于 dict 传递结构化数据
