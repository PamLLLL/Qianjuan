from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class QualityIssue(Base):
    __tablename__ = "quality_issues"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    report_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("quality_reports.id"))
    chapter_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("chapters.id"), nullable=True
    )
    severity: Mapped[str] = mapped_column(String(20))
    category: Mapped[str] = mapped_column(String(50))
    chapter_title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    description: Mapped[str] = mapped_column(Text)
    original_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    suggestion: Mapped[str | None] = mapped_column(Text, nullable=True)
    fix_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    fix_status: Mapped[str] = mapped_column(String(20), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    report: Mapped["QualityReport"] = relationship(back_populates="issues")
