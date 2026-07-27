# 模型层约定

- 所有模型继承 `Base`（from app.database）
- 使用 SQLAlchemy 2.0 声明式：`Mapped[type]` + `mapped_column()`
- UUID 主键：`default=uuid.uuid4`
- 时间戳字段用 `server_default=func.now()`
- JSON 字段存储复杂结构（列表、嵌套对象）
- 1:1 关系：外键加 `unique=True`
- 1:N 关系：父表 `relationship(cascade="all, delete-orphan")`
- 每个模型文件只定义一个模型类
- 模型类名单数（Project），表名复数（projects）
