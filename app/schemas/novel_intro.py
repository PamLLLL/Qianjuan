from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict


class LeadCharacter(BaseModel):
    name: str
    tag: str
    role: str


class NovelIntroResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    title_candidates: list | None
    selected_title: str | None
    hook_line: str | None
    lead_characters: list | None
    cp_line: str | None
    tags: list | None
    synopsis: str | None


class NovelIntroUpdate(BaseModel):
    selected_title: str | None = None
    hook_line: str | None = None
    lead_characters: list[LeadCharacter] | None = None
    cp_line: str | None = None
    tags: list[str] | None = None
    synopsis: str | None = None
