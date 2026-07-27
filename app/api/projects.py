from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.schemas.project import (
    ProjectCreate,
    ProjectListResponse,
    ProjectResponse,
    ProjectUpdate,
)
from app.services import project_service

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.get("", response_model=ProjectListResponse)
async def list_projects(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
):
    items, total = await project_service.list_projects(session, page, size)
    return ProjectListResponse(
        items=[ProjectResponse.model_validate(p) for p in items],
        total=total,
        page=page,
        size=size,
        pages=project_service.calc_pages(total, size),
    )


@router.post("", response_model=ProjectResponse, status_code=201)
async def create_project(
    data: ProjectCreate,
    session: AsyncSession = Depends(get_session),
):
    project = await project_service.create_project(session, data)
    return ProjectResponse.model_validate(project)


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    project = await project_service.get_project(session, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    return ProjectResponse.model_validate(project)


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: uuid.UUID,
    data: ProjectUpdate,
    session: AsyncSession = Depends(get_session),
):
    project = await project_service.update_project(session, project_id, data)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    return ProjectResponse.model_validate(project)


@router.delete("/{project_id}", status_code=204)
async def delete_project(
    project_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    deleted = await project_service.delete_project(session, project_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="项目不存在")
