---
paths:
  - "app/models/**/*.py"
---

# SQLAlchemy 模型规范

- 所有模型继承 `Base`（from app.database import Base）
- 使用 `Mapped[type]` 和 `mapped_column()` 声明式风格
- UUID 主键：`id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)`
- 时间戳：`created_at: Mapped[datetime] = mapped_column(default=func.now())`
- JSON 字段：`Mapped[dict | None] = mapped_column(JSON, nullable=True)`
- 外键命名：`{table}_id`，如 `project_id`
- 关系用 `relationship()`，配合 `back_populates`
- 1:1 关系在外键加 `unique=True`
- 级联删除在 relationship 设置 `cascade="all, delete-orphan"`
- 表名用 `__tablename__` 显式指定，复数形式
