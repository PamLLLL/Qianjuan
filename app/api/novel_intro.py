from __future__ import annotations

import json
import uuid
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sse_starlette.sse import EventSourceResponse

from app.database import get_session
from app.models.novel_intro import NovelIntro
from app.models.project import Project
from app.schemas.novel_intro import NovelIntroResponse, NovelIntroUpdate
from app.services import novel_intro_service

router = APIRouter(prefix="/api/novel-intro", tags=["novel-intro"])


@router.post("/generate/{project_id}")
async def generate_intro(
    project_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    stmt = (
        select(Project)
        .where(Project.id == project_id)
        .options(
            selectinload(Project.setting),
            selectinload(Project.characters),
            selectinload(Project.outline),
            selectinload(Project.novel_intro),
        )
    )
    result = await session.execute(stmt)
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    if project.novel_intro:
        raise HTTPException(status_code=409, detail="小说介绍已存在")

    gen = novel_intro_service.generate_novel_intro(session, project)

    async def stream() -> AsyncGenerator[dict, None]:
        try:
            async for chunk in gen:
                yield {"data": json.dumps({"type": "chunk", "content": chunk}, ensure_ascii=False)}
            yield {"data": "[DONE]"}
        except Exception as e:
            yield {"data": json.dumps({"type": "error", "message": str(e)}, ensure_ascii=False)}

    return EventSourceResponse(stream())


@router.get("/{project_id}", response_model=NovelIntroResponse)
async def get_intro(
    project_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    stmt = select(NovelIntro).where(NovelIntro.project_id == project_id)
    result = await session.execute(stmt)
    intro = result.scalar_one_or_none()
    if not intro:
        raise HTTPException(status_code=404, detail="小说介绍不存在")
    return NovelIntroResponse.model_validate(intro)


@router.put("/{project_id}", response_model=NovelIntroResponse)
async def update_intro(
    project_id: uuid.UUID,
    body: NovelIntroUpdate,
    session: AsyncSession = Depends(get_session),
):
    stmt = select(NovelIntro).where(NovelIntro.project_id == project_id)
    result = await session.execute(stmt)
    intro = result.scalar_one_or_none()
    if not intro:
        raise HTTPException(status_code=404, detail="小说介绍不存在")

    update_data = body.model_dump(exclude_unset=True)
    if "lead_characters" in update_data and update_data["lead_characters"]:
        update_data["lead_characters"] = [c.model_dump() for c in update_data["lead_characters"]]
    for key, value in update_data.items():
        setattr(intro, key, value)

    await session.flush()
    await session.refresh(intro)
    return NovelIntroResponse.model_validate(intro)
