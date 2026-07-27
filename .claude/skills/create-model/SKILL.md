---
name: create-model
description: 创建新的 SQLAlchemy 异步模型（含表结构、关系、Pydantic schema、测试）
---

## 步骤

1. 在 `app/models/` 下创建 `{name}.py`
   - 继承 Base，设置 `__tablename__`
   - 使用 `Mapped[]` + `mapped_column()` 声明字段
   - UUID 主键，datetime 时间戳
   - 定义外键和 relationship

2. 在 `app/models/__init__.py` 中导入新模型

3. 在 `app/schemas/` 下创建或更新对应的 Pydantic schema
   - Create / Update / Response 三种模型
   - `model_config = ConfigDict(from_attributes=True)`

4. 在 `tests/test_models/` 下创建测试
   - 测试建表、插入、查询、关系、级联删除

5. 运行 `pytest tests/test_models/test_{name}.py` 验证
