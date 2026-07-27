from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Chapter(Base):
    __tablename__ = "chapters"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"))
    volume_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("volumes.id"))
    title: Mapped[str] = mapped_column(String(200))
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    detailed_outline: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    word_target: Mapped[int] = mapped_column(Integer, default=3000)
    word_count: Mapped[int] = mapped_column(Integer, default=0)
    characters_involved: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    emotional_tone: Mapped[str | None] = mapped_column(String(100), nullable=True)
    chapter_hook: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_provider: Mapped[str | None] = mapped_column(String(50), nullable=True)
    ai_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    draft_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="draft")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    project: Mapped[Project] = relationship("Project")
    volume: Mapped[Volume] = relationship("Volume", back_populates="chapters")
    versions: Mapped[list[Version]] = relationship(
        "Version", back_populates="chapter", cascade="all, delete-orphan"
    )
    narrative_snapshot: Mapped[NarrativeSnapshot | None] = relationship(
        "NarrativeSnapshot",
        back_populates="chapter",
        uselist=False,
        cascade="all, delete-orphan",
    )
