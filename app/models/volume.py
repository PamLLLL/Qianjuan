from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Volume(Base):
    __tablename__ = "volumes"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"))
    title: Mapped[str] = mapped_column(String(200))
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    word_target: Mapped[int] = mapped_column(Integer, default=0)
    key_arc: Mapped[str | None] = mapped_column(Text, nullable=True)
    start_state: Mapped[str | None] = mapped_column(Text, nullable=True)
    end_state: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    project: Mapped[Project] = relationship("Project", back_populates="volumes")
    chapters: Mapped[list[Chapter]] = relationship(
        "Chapter", back_populates="volume", cascade="all, delete-orphan"
    )
