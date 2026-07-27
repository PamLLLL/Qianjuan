from __future__ import annotations

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.database import Base


class GlobalConfig(Base):
    __tablename__ = "global_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    default_provider: Mapped[str] = mapped_column(String(50), default="deepseek")
    default_model: Mapped[str] = mapped_column(String(100), default="deepseek-chat")
    ui_preferences: Mapped[dict | None] = mapped_column(JSON, nullable=True)
