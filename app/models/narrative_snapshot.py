from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.database import Base


class NarrativeSnapshot(Base):
    __tablename__ = "narrative_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"))
    chapter_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("chapters.id"), unique=True)
    characters_state: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    plot_hooks: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    timeline: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    items: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    world_rules: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="current")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    chapter: Mapped["Chapter"] = relationship(back_populates="narrative_snapshot")
