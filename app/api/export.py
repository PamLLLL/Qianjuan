from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.services import export_service

router = APIRouter(prefix="/api/export", tags=["export"])


class ExportRequest(BaseModel):
    format: str = Field(default="txt", pattern="^(txt|docx|epub)$")
    scope: str = Field(default="all", pattern="^(all|volume|chapter)$")
    volume_id: uuid.UUID | None = None
    chapter_id: uuid.UUID | None = None


@router.post("/{project_id}")
async def export_project(
    project_id: uuid.UUID,
    body: ExportRequest,
    session: AsyncSession = Depends(get_session),
):
    """Export project as TXT/DOCX/EPUB. Returns file download."""
    try:
        filepath, filename = await export_service.export_project(
            session=session,
            project_id=project_id,
            fmt=body.format,
            scope=body.scope,
            volume_id=body.volume_id,
            chapter_id=body.chapter_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    media_types = {
        "txt": "text/plain; charset=utf-8",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "epub": "application/epub+zip",
    }

    return FileResponse(
        path=str(filepath),
        filename=filename,
        media_type=media_types.get(body.format, "application/octet-stream"),
    )
