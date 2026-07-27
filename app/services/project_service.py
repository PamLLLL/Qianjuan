from __future__ import annotations

import math
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project
from app.schemas.project import ProjectCreate, ProjectUpdate


async def create_project(session: AsyncSession, data: ProjectCreate) -> Project:
    project = Project(
        id=uuid.uuid4(),
        name=data.name,
        genre=data.genre,
        concept=data.concept,
        target_words=data.target_words,
        target_platform=data.target_platform,
        style_preset=data.style_preset,
        custom_style=data.custom_style,
        ai_provider=data.ai_provider,
    )
    session.add(project)
    await session.flush()
    return project


async def get_project(session: AsyncSession, project_id: uuid.UUID) -> Project | None:
    return await session.get(Project, project_id)


async def list_projects(
    session: AsyncSession, page: int = 1, size: int = 20
) -> tuple[list[Project], int]:
    count_stmt = select(func.count()).select_from(Project)
    total = (await session.execute(count_stmt)).scalar() or 0

    offset = (page - 1) * size
    stmt = (
        select(Project)
        .order_by(Project.updated_at.desc())
        .offset(offset)
        .limit(size)
    )
    result = await session.execute(stmt)
    items = list(result.scalars().all())
    return items, total


async def update_project(
    session: AsyncSession, project_id: uuid.UUID, data: ProjectUpdate
) -> Project | None:
    project = await session.get(Project, project_id)
    if not project:
        return None
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(project, key, value)
    await session.flush()
    await session.refresh(project)
    return project


async def delete_project(session: AsyncSession, project_id: uuid.UUID) -> bool:
    project = await session.get(Project, project_id)
    if not project:
        return False
    await session.delete(project)
    await session.flush()
    return True


def calc_pages(total: int, size: int) -> int:
    return max(1, math.ceil(total / size))
