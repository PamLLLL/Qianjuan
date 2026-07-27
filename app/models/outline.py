from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Outline(Base):
    __tablename__ = "outlines"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id"), unique=True
    )
    premise: Mapped[str | None] = mapped_column(Text, nullable=True)
    act_one: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    act_two: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    act_three: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    subplots: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    foreshadowing: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    project: Mapped[Project] = relationship("Project", back_populates="outline")
