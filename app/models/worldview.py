from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Worldview(Base):
    __tablename__ = "worldviews"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id"), unique=True
    )
    world_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    geography: Mapped[str | None] = mapped_column(Text, nullable=True)
    society: Mapped[str | None] = mapped_column(Text, nullable=True)
    power_system: Mapped[str | None] = mapped_column(Text, nullable=True)
    history: Mapped[str | None] = mapped_column(Text, nullable=True)
    rules: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    culture: Mapped[str | None] = mapped_column(Text, nullable=True)
    technology: Mapped[str | None] = mapped_column(Text, nullable=True)

    project: Mapped[Project] = relationship("Project", back_populates="worldview")
