from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ChapterResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    volume_id: uuid.UUID
    title: str
    summary: str | None
    content: str | None
    detailed_outline: dict | None
    word_target: int
    word_count: int
    characters_involved: list | None
    emotional_tone: str | None
    chapter_hook: str | None
    ai_provider: str | None
    ai_model: str | None
    status: str
    sort_order: int
    created_at: datetime
    updated_at: datetime


class ChapterUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=200)
    summary: str | None = None
    content: str | None = None
    word_target: int | None = Field(default=None, gt=0)
    emotional_tone: str | None = None
    chapter_hook: str | None = None


class ChapterContentUpdate(BaseModel):
    content: str


class ChapterWordTargetUpdate(BaseModel):
    word_target: int = Field(gt=0)


class VersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    chapter_id: uuid.UUID
    operation_type: str
    created_at: datetime
