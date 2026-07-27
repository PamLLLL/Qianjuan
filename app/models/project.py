from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200))
    genre: Mapped[str] = mapped_column(String(100))
    concept: Mapped[str] = mapped_column(Text)
    target_words: Mapped[int] = mapped_column(Integer)
    actual_words: Mapped[int] = mapped_column(Integer, default=0)
    target_platform: Mapped[str] = mapped_column(String(50))
    style_preset: Mapped[str | None] = mapped_column(String(50), nullable=True)
    custom_style: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_provider: Mapped[str | None] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="draft")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    # 1:1 relationships
    setting: Mapped[ProjectSetting | None] = relationship(
        "ProjectSetting", back_populates="project", uselist=False, cascade="all, delete-orphan"
    )
    worldview: Mapped[Worldview | None] = relationship(
        "Worldview", back_populates="project", uselist=False, cascade="all, delete-orphan"
    )
    outline: Mapped[Outline | None] = relationship(
        "Outline", back_populates="project", uselist=False, cascade="all, delete-orphan"
    )
    novel_intro: Mapped[NovelIntro | None] = relationship(
        "NovelIntro", back_populates="project", uselist=False, cascade="all, delete-orphan"
    )

    # 1:N relationships
    characters: Mapped[list[Character]] = relationship(
        "Character", back_populates="project", cascade="all, delete-orphan"
    )
    volumes: Mapped[list[Volume]] = relationship(
        "Volume", back_populates="project", cascade="all, delete-orphan"
    )
    quality_reports: Mapped[list[QualityReport]] = relationship(
        "QualityReport", back_populates="project", cascade="all, delete-orphan"
    )
    generation_tasks: Mapped[list[GenerationTask]] = relationship(
        "GenerationTask", back_populates="project", cascade="all, delete-orphan"
    )
