from __future__ import annotations

import json
import uuid
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select
from sse_starlette.sse import EventSourceResponse

from app.database import get_session
from app.models.project import Project
from app.services import generation_service

router = APIRouter(prefix="/api/generate", tags=["generate"])


async def _get_project_with_relations(
    session: AsyncSession, project_id: uuid.UUID
) -> Project:
    stmt = (
        select(Project)
        .where(Project.id == project_id)
        .options(
            selectinload(Project.setting),
            selectinload(Project.characters),
            selectinload(Project.worldview),
            selectinload(Project.outline),
            selectinload(Project.volumes),
        )
    )
    result = await session.execute(stmt)
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    return project


async def _stream_wrapper(
    gen: AsyncGenerator[str, None],
) -> AsyncGenerator[dict, None]:
    """Wrap generation stream into SSE event dicts."""
    try:
        async for chunk in gen:
            yield {"data": json.dumps({"type": "chunk", "content": chunk}, ensure_ascii=False)}
        yield {"data": "[DONE]"}
    except Exception as e:
        yield {"data": json.dumps({"type": "error", "message": str(e)}, ensure_ascii=False)}


@router.post("/settings/{project_id}")
async def generate_settings(
    project_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    project = await _get_project_with_relations(session, project_id)
    if project.setting:
        raise HTTPException(status_code=409, detail="基础设定已存在，请先删除后重新生成")

    gen = generation_service.generate_settings(session, project)
    return EventSourceResponse(_stream_wrapper(gen))


@router.post("/characters/{project_id}")
async def generate_characters(
    project_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    project = await _get_project_with_relations(session, project_id)

    gen = generation_service.generate_characters(session, project)
    return EventSourceResponse(_stream_wrapper(gen))


@router.post("/worldview/{project_id}")
async def generate_worldview(
    project_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    project = await _get_project_with_relations(session, project_id)
    if project.worldview:
        raise HTTPException(status_code=409, detail="世界观已存在，请先删除后重新生成")

    gen = generation_service.generate_worldview(session, project)
    return EventSourceResponse(_stream_wrapper(gen))


@router.post("/outline/{project_id}")
async def generate_outline(
    project_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    project = await _get_project_with_relations(session, project_id)
    if project.outline:
        raise HTTPException(status_code=409, detail="故事大纲已存在，请先删除后重新生成")

    gen = generation_service.generate_outline(session, project)
    return EventSourceResponse(_stream_wrapper(gen))
