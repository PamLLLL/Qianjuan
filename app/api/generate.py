from __future__ import annotations

import json
import uuid
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select
from sse_starlette.sse import EventSourceResponse

from pydantic import BaseModel, Field

from app.database import get_session
from app.models.chapter import Chapter
from app.models.generation_task import GenerationTask
from app.models.project import Project
from app.models.volume import Volume
from app.services import generation_service, task_service


class ChapterContentRequest(BaseModel):
    word_target: int | None = Field(default=None, gt=0)

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


@router.post("/volumes/{project_id}")
async def generate_volumes(
    project_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    project = await _get_project_with_relations(session, project_id)
    if not project.outline:
        raise HTTPException(status_code=400, detail="请先生成故事大纲")
    if project.volumes:
        raise HTTPException(status_code=409, detail="分卷结构已存在，请先删除后重新生成")

    gen = generation_service.generate_volumes(session, project)
    return EventSourceResponse(_stream_wrapper(gen))


@router.post("/chapter-outlines/{volume_id}")
async def generate_chapter_outlines(
    volume_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    volume = await session.get(Volume, volume_id)
    if not volume:
        raise HTTPException(status_code=404, detail="分卷不存在")

    project = await _get_project_with_relations(session, volume.project_id)

    gen = generation_service.generate_chapter_outlines(session, project, volume)
    return EventSourceResponse(_stream_wrapper(gen))


@router.post("/chapter-content/{chapter_id}")
async def generate_chapter_content(
    chapter_id: uuid.UUID,
    body: ChapterContentRequest | None = None,
    session: AsyncSession = Depends(get_session),
):
    chapter = await session.get(Chapter, chapter_id)
    if not chapter:
        raise HTTPException(status_code=404, detail="章节不存在")

    project = await _get_project_with_relations(session, chapter.project_id)
    word_target = body.word_target if body else None

    gen = generation_service.generate_chapter_content(
        session, project, chapter, word_target
    )
    return EventSourceResponse(_stream_wrapper(gen))


@router.post("/auto/{project_id}")
async def auto_generate(
    project_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    """Start full-auto generation (F20). SSE stream with step progress."""
    project = await _get_project_with_relations(session, project_id)
    task = await task_service.start_auto_generation(session, project_id)

    async def stream() -> AsyncGenerator[dict, None]:
        try:
            async for event in task_service.run_auto_steps(session, task):
                yield {"data": event}
            yield {"data": "[DONE]"}
        except Exception as e:
            yield {"data": json.dumps({"type": "error", "message": str(e)}, ensure_ascii=False)}

    return EventSourceResponse(stream())


@router.post("/cancel/{task_id}")
async def cancel_generation(
    task_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    success = await task_service.cancel_task(session, task_id)
    if not success:
        raise HTTPException(status_code=404, detail="任务不存在")
    return {"message": "任务已取消"}


@router.get("/task/{project_id}")
async def get_task_status(
    project_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    task = await task_service.get_task(session, project_id)
    if not task:
        raise HTTPException(status_code=404, detail="没有生成任务")
    return {
        "id": str(task.id),
        "current_step": task.current_step,
        "step_status": task.step_status,
        "progress": task.progress,
        "error_message": task.error_message,
    }
