from __future__ import annotations

import asyncio
import json
import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.chapter import Chapter
from app.models.generation_task import GenerationTask
from app.models.project import Project
from app.models.volume import Volume
from app.services import generation_service

logger = logging.getLogger(__name__)

STEP_ORDER = [
    "pending", "settings", "characters", "worldview", "outline",
    "volumes", "chapter_outlines", "content_generating",
    "content_done", "completed",
]

_running_tasks: dict[uuid.UUID, bool] = {}


async def start_auto_generation(
    session: AsyncSession, project_id: uuid.UUID
) -> GenerationTask:
    """Create and start a full-auto generation task (F20)."""
    task = GenerationTask(
        id=uuid.uuid4(),
        project_id=project_id,
        current_step="pending",
        step_status="running",
        progress={"total_chapters": 0, "completed_chapters": 0},
    )
    session.add(task)
    await session.flush()
    _running_tasks[task.id] = True
    return task


async def cancel_task(session: AsyncSession, task_id: uuid.UUID) -> bool:
    """Cancel a running task."""
    task = await session.get(GenerationTask, task_id)
    if not task:
        return False
    _running_tasks.pop(task_id, None)
    task.step_status = "paused"
    await session.flush()
    return True


async def get_task(session: AsyncSession, project_id: uuid.UUID) -> GenerationTask | None:
    """Get the latest generation task for a project."""
    stmt = (
        select(GenerationTask)
        .where(GenerationTask.project_id == project_id)
        .order_by(GenerationTask.started_at.desc())
        .limit(1)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def run_auto_steps(
    session: AsyncSession, task: GenerationTask
):
    """Execute all generation steps sequentially. Yields progress events."""
    project = await _load_project(session, task.project_id)
    if not project:
        task.step_status = "failed"
        task.error_message = "项目不存在"
        return

    steps = [
        ("settings", _step_settings),
        ("characters", _step_characters),
        ("worldview", _step_worldview),
        ("outline", _step_outline),
        ("volumes", _step_volumes),
        ("chapter_outlines", _step_chapter_outlines),
        ("content_generating", _step_content),
    ]

    for step_name, step_func in steps:
        if not _running_tasks.get(task.id, False):
            task.step_status = "paused"
            yield json.dumps({"type": "status", "step": step_name, "status": "paused"})
            return

        task.current_step = step_name
        task.step_status = "running"
        await session.flush()

        yield json.dumps({"type": "step_start", "step": step_name})

        try:
            project = await _load_project(session, task.project_id)
            async for chunk in step_func(session, project, task):
                yield json.dumps({"type": "chunk", "content": chunk})
        except Exception as e:
            task.step_status = "failed"
            task.error_message = str(e)
            await session.flush()
            yield json.dumps({"type": "error", "step": step_name, "message": str(e)})
            return

        yield json.dumps({"type": "step_done", "step": step_name})

    task.current_step = "completed"
    task.step_status = "completed"
    _running_tasks.pop(task.id, None)
    await session.flush()
    yield json.dumps({"type": "completed"})


async def _step_settings(session, project, task):
    if project.setting:
        return
    async for chunk in generation_service.generate_settings(session, project):
        yield chunk


async def _step_characters(session, project, task):
    if project.characters:
        return
    async for chunk in generation_service.generate_characters(session, project):
        yield chunk


async def _step_worldview(session, project, task):
    if project.worldview:
        return
    async for chunk in generation_service.generate_worldview(session, project):
        yield chunk


async def _step_outline(session, project, task):
    if project.outline:
        return
    async for chunk in generation_service.generate_outline(session, project):
        yield chunk


async def _step_volumes(session, project, task):
    if project.volumes:
        return
    async for chunk in generation_service.generate_volumes(session, project):
        yield chunk


async def _step_chapter_outlines(session, project, task):
    for volume in project.volumes:
        stmt = select(Chapter).where(Chapter.volume_id == volume.id).limit(1)
        result = await session.execute(stmt)
        if result.scalar_one_or_none():
            continue
        async for chunk in generation_service.generate_chapter_outlines(session, project, volume):
            yield chunk


async def _step_content(session, project, task):
    stmt = (
        select(Chapter)
        .where(Chapter.project_id == project.id, Chapter.content.is_(None))
        .order_by(Chapter.sort_order)
    )
    result = await session.execute(stmt)
    chapters = list(result.scalars().all())

    task.progress = {"total_chapters": len(chapters), "completed_chapters": 0}
    await session.flush()

    for i, chapter in enumerate(chapters):
        if not _running_tasks.get(task.id, False):
            return

        project = await _load_project(session, project.id)
        async for chunk in generation_service.generate_chapter_content(
            session, project, chapter
        ):
            yield chunk

        task.progress = {"total_chapters": len(chapters), "completed_chapters": i + 1}
        await session.flush()


async def _load_project(session: AsyncSession, project_id: uuid.UUID) -> Project | None:
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
    return result.scalar_one_or_none()
