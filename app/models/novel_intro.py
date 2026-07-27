from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.database import Base


class NovelIntro(Base):
    __tablename__ = "novel_intros"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"), unique=True)
    title_candidates: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    selected_title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    hook_line: Mapped[str | None] = mapped_column(Text, nullable=True)
    lead_characters: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    cp_line: Mapped[str | None] = mapped_column(String(200), nullable=True)
    tags: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    synopsis: Mapped[str | None] = mapped_column(Text, nullable=True)

    project: Mapped["Project"] = relationship(back_populates="novel_intro")
