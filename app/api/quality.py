from __future__ import annotations

import json
import uuid
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sse_starlette.sse import EventSourceResponse

from sqlalchemy import func as sa_func

from app.database import get_session
from app.models.ai_usage_log import AiUsageLog
from app.models.chapter import Chapter
from app.models.project import Project
from app.models.quality_issue import QualityIssue
from app.models.volume import Volume
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


@router.get("/stats/{project_id}")
async def get_project_stats(
    project_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    """Word count dashboard data (F26) + AI usage stats."""
    project = await session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    # Volume stats
    vol_stmt = (
        select(Volume)
        .where(Volume.project_id == project_id)
        .order_by(Volume.sort_order)
    )
    volumes = list((await session.execute(vol_stmt)).scalars().all())

    volume_stats = []
    total_words = 0
    total_chapters = 0
    completed_chapters = 0

    for vol in volumes:
        ch_stmt = (
            select(Chapter)
            .where(Chapter.volume_id == vol.id)
            .order_by(Chapter.sort_order)
        )
        chapters = list((await session.execute(ch_stmt)).scalars().all())
        vol_words = sum(ch.word_count or 0 for ch in chapters)
        vol_done = sum(1 for ch in chapters if ch.content)
        total_words += vol_words
        total_chapters += len(chapters)
        completed_chapters += vol_done

        chapter_stats = [
            {
                "id": str(ch.id),
                "title": ch.title,
                "word_count": ch.word_count or 0,
                "word_target": ch.word_target or 0,
                "status": ch.status,
            }
            for ch in chapters
        ]

        volume_stats.append({
            "id": str(vol.id),
            "title": vol.title,
            "word_target": vol.word_target,
            "word_actual": vol_words,
            "chapter_count": len(chapters),
            "chapters_done": vol_done,
            "chapters": chapter_stats,
        })

    # AI usage stats
    usage_stmt = select(
        sa_func.coalesce(sa_func.sum(AiUsageLog.input_tokens), 0),
        sa_func.coalesce(sa_func.sum(AiUsageLog.output_tokens), 0),
        sa_func.coalesce(sa_func.sum(AiUsageLog.estimated_cost_usd), 0),
    ).where(AiUsageLog.project_id == project_id)
    usage = (await session.execute(usage_stmt)).one()

    return {
        "project_id": str(project_id),
        "target_words": project.target_words,
        "actual_words": total_words,
        "progress_pct": round(total_words / max(project.target_words, 1) * 100, 1),
        "total_chapters": total_chapters,
        "completed_chapters": completed_chapters,
        "volumes": volume_stats,
        "ai_usage": {
            "total_input_tokens": int(usage[0]),
            "total_output_tokens": int(usage[1]),
            "estimated_cost_usd": float(usage[2]),
        },
    }


@router.post("/dedup-check/{project_id}")
async def dedup_check(
    project_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    """Content deduplication check (F27): detect repeated paragraphs."""
    ch_stmt = (
        select(Chapter)
        .where(Chapter.project_id == project_id, Chapter.content.isnot(None))
        .order_by(Chapter.sort_order)
    )
    chapters = list((await session.execute(ch_stmt)).scalars().all())
    if not chapters:
        raise HTTPException(status_code=400, detail="没有可检测的章节内容")

    duplicates = []
    seen_segments: dict[str, str] = {}

    for ch in chapters:
        content = ch.content or ""
        paragraphs = [p.strip() for p in content.split("\n") if len(p.strip()) > 30]

        for para in paragraphs:
            key = para[:50]
            if key in seen_segments and seen_segments[key] != ch.title:
                duplicates.append({
                    "text": para[:100] + "..." if len(para) > 100 else para,
                    "found_in": [seen_segments[key], ch.title],
                    "length": len(para),
                })
            else:
                seen_segments[key] = ch.title

    return {
        "project_id": str(project_id),
        "total_chapters_checked": len(chapters),
        "duplicates_found": len(duplicates),
        "duplicates": duplicates[:50],
    }
