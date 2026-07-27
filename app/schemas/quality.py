from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class QualityIssueResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    report_id: uuid.UUID
    chapter_id: uuid.UUID | None
    severity: str
    category: str
    chapter_title: str | None
    description: str
    original_text: str | None
    suggestion: str | None
    fix_content: str | None
    fix_status: str
    created_at: datetime


class QualityReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    overall_score: int | None
    strengths: list | None
    summary: str | None
    issues: list[QualityIssueResponse] = []
    created_at: datetime
