from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ProjectCreate(BaseModel):
    name: str = Field(max_length=200)
    genre: str = Field(max_length=100)
    concept: str
    target_words: int = Field(gt=0)
    target_platform: str = Field(max_length=50)
    style_preset: str | None = None
    custom_style: str | None = None
    ai_provider: str | None = None


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=200)
    genre: str | None = None
    concept: str | None = None
    target_words: int | None = Field(default=None, gt=0)
    target_platform: str | None = None
    style_preset: str | None = None
    custom_style: str | None = None
    ai_provider: str | None = None
    status: str | None = None


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    genre: str
    concept: str
    target_words: int
    actual_words: int
    target_platform: str
    style_preset: str | None
    custom_style: str | None
    ai_provider: str | None
    status: str
    created_at: datetime
    updated_at: datetime


class ProjectListResponse(BaseModel):
    items: list[ProjectResponse]
    total: int
    page: int
    size: int
    pages: int
