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
from app.models.project import Project
from app.models.quality_issue import QualityIssue
from app.models.quality_report import QualityReport
from app.schemas.quality import QualityIssueResponse, QualityReportResponse
from app.services import quality_service

router = APIRouter(prefix="/api/quality", tags=["quality"])


@router.post("/check/{project_id}")
async def run_quality_check(
    project_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    stmt = (
        select(Project)
        .where(Project.id == project_id)
        .options(
            selectinload(Project.setting),
            selectinload(Project.characters),
            selectinload(Project.worldview),
        )
    )
    result = await session.execute(stmt)
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    async def stream_wrapper() -> AsyncGenerator[dict, None]:
        try:
            async for chunk in quality_service.run_quality_check(session, project):
                yield {"data": json.dumps({"type": "chunk", "content": chunk}, ensure_ascii=False)}
            yield {"data": "[DONE]"}
        except Exception as e:
            yield {"data": json.dumps({"type": "error", "message": str(e)}, ensure_ascii=False)}

    return EventSourceResponse(stream_wrapper())


@router.post("/suggest-fix/{issue_id}", response_model=QualityIssueResponse)
async def suggest_fix(
    issue_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    issue = await session.get(QualityIssue, issue_id)
    if not issue:
        raise HTTPException(status_code=404, detail="问题不存在")

    report = await session.get(QualityReport, issue.report_id)
    if not report:
        raise HTTPException(status_code=404, detail="报告不存在")

    project = await session.get(Project, report.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    await quality_service.suggest_fix(session, issue, project)
    await session.flush()
    await session.refresh(issue)
    return QualityIssueResponse.model_validate(issue)


@router.post("/apply-fix/{issue_id}", response_model=QualityIssueResponse)
async def apply_fix(
    issue_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    issue = await session.get(QualityIssue, issue_id)
    if not issue:
        raise HTTPException(status_code=404, detail="问题不存在")
    if issue.fix_status != "suggested" and issue.fix_status != "confirmed":
        raise HTTPException(status_code=400, detail="请先生成修复方案")

    success = await quality_service.apply_fix(session, issue)
    if not success:
        raise HTTPException(status_code=400, detail="修复失败")

    await session.flush()
    await session.refresh(issue)
    return QualityIssueResponse.model_validate(issue)


@router.post("/skip/{issue_id}", response_model=QualityIssueResponse)
async def skip_issue(
    issue_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    issue = await session.get(QualityIssue, issue_id)
    if not issue:
        raise HTTPException(status_code=404, detail="问题不存在")

    issue.fix_status = "skipped"
    await session.flush()
    await session.refresh(issue)
    return QualityIssueResponse.model_validate(issue)


@router.get("/reports/{project_id}", response_model=list[QualityReportResponse])
async def get_reports(
    project_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    stmt = (
        select(QualityReport)
        .where(QualityReport.project_id == project_id)
        .options(selectinload(QualityReport.issues))
        .order_by(QualityReport.created_at.desc())
    )
    result = await session.execute(stmt)
    reports = list(result.scalars().all())
    return [QualityReportResponse.model_validate(r) for r in reports]
