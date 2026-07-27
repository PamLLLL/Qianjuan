from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ProjectSetting(Base):
    __tablename__ = "project_settings"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id"), unique=True
    )
    title_suggestions: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    background: Mapped[str | None] = mapped_column(Text, nullable=True)
    tone: Mapped[str | None] = mapped_column(String(100), nullable=True)
    core_conflict: Mapped[str | None] = mapped_column(Text, nullable=True)
    themes: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    target_audience: Mapped[str | None] = mapped_column(Text, nullable=True)
    unique_selling_point: Mapped[str | None] = mapped_column(Text, nullable=True)

    project: Mapped[Project] = relationship("Project", back_populates="setting")
