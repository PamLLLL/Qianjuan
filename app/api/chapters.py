from __future__ import annotations

import json
import uuid
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sse_starlette.sse import EventSourceResponse

from app.core.ai import registry
from app.database import get_session
from app.models.chapter import Chapter
from app.models.project import Project
from app.models.version import Version
from app.schemas.chapter import (
    ChapterContentUpdate,
    ChapterResponse,
    ChapterWordTargetUpdate,
    VersionResponse,
)
from app.services.rules_engine import RulesEngine

router = APIRouter(prefix="/api/chapters", tags=["chapters"])
rules = RulesEngine()

MAX_VERSIONS_PER_CHAPTER = 10


async def _save_version(session: AsyncSession, chapter: Chapter, op_type: str) -> None:
    """Save current content as a version before modification."""
    if not chapter.content:
        return

    version = Version(
        id=uuid.uuid4(),
        chapter_id=chapter.id,
        content=chapter.content,
        operation_type=op_type,
    )
    session.add(version)

    stmt = (
        select(Version)
        .where(Version.chapter_id == chapter.id)
        .order_by(Version.created_at.asc())
    )
    result = await session.execute(stmt)
    versions = list(result.scalars().all())
    if len(versions) >= MAX_VERSIONS_PER_CHAPTER:
        for old in versions[: len(versions) - MAX_VERSIONS_PER_CHAPTER + 1]:
            await session.delete(old)


@router.put("/{chapter_id}/content", response_model=ChapterResponse)
async def update_content(
    chapter_id: uuid.UUID,
    body: ChapterContentUpdate,
    session: AsyncSession = Depends(get_session),
):
    chapter = await session.get(Chapter, chapter_id)
    if not chapter:
        raise HTTPException(status_code=404, detail="章节不存在")

    await _save_version(session, chapter, "before_manual_edit")
    chapter.content = body.content
    chapter.word_count = len(body.content)
    chapter.status = "edited"
    await session.flush()
    await session.refresh(chapter)
    return ChapterResponse.model_validate(chapter)


@router.put("/{chapter_id}/word-target", response_model=ChapterResponse)
async def update_word_target(
    chapter_id: uuid.UUID,
    body: ChapterWordTargetUpdate,
    session: AsyncSession = Depends(get_session),
):
    chapter = await session.get(Chapter, chapter_id)
    if not chapter:
        raise HTTPException(status_code=404, detail="章节不存在")

    chapter.word_target = body.word_target
    await session.flush()
    await session.refresh(chapter)
    return ChapterResponse.model_validate(chapter)


@router.post("/{chapter_id}/expand")
async def expand_chapter(
    chapter_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    """AI expand: add ~500 words to the chapter (F18)."""
    chapter = await session.get(Chapter, chapter_id)
    if not chapter:
        raise HTTPException(status_code=404, detail="章节不存在")
    if not chapter.content:
        raise HTTPException(status_code=400, detail="章节无内容可扩写")

    project = await _get_project(session, chapter.project_id)
    await _save_version(session, chapter, "before_expand")

    system_prompt = rules.build_system_prompt(
        platform=project.target_platform,
        style=project.style_preset,
        genre=project.genre,
    )
    user_prompt = f"""请对以下小说章节进行扩写，增加约500字的内容。

## 扩写要求
- 在现有段落之间自然插入新内容
- 增加感官描写、动作细节、环境描写
- 丰富对话，增加角色互动
- 保持原有情节和节奏不变
- 不要在开头或结尾简单添加，要融入正文各处

## 原文
{chapter.content}

请直接输出扩写后的完整正文。"""

    provider = registry.get_provider(project.ai_provider)

    async def stream():
        full = ""
        try:
            async for chunk in provider.stream_generate(system_prompt, user_prompt):
                full += chunk
                yield {"data": json.dumps({"type": "chunk", "content": chunk}, ensure_ascii=False)}
            chapter.content = full
            chapter.word_count = len(full)
            yield {"data": "[DONE]"}
        except Exception as e:
            yield {"data": json.dumps({"type": "error", "message": str(e)}, ensure_ascii=False)}

    return EventSourceResponse(stream())


@router.post("/{chapter_id}/polish")
async def polish_chapter(
    chapter_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    """De-AI-flavor polish (F19): replace AI patterns with natural writing."""
    chapter = await session.get(Chapter, chapter_id)
    if not chapter:
        raise HTTPException(status_code=404, detail="章节不存在")
    if not chapter.content:
        raise HTTPException(status_code=400, detail="章节无内容可润色")

    project = await _get_project(session, chapter.project_id)
    await _save_version(session, chapter, "before_polish")

    system_prompt = rules.build_system_prompt(
        platform=project.target_platform,
        style=project.style_preset,
        genre=project.genre,
    )
    polish_rules = rules.load_generation_rules("polish")

    user_prompt = f"""{polish_rules}

## 待润色原文
{chapter.content}

请按照润色规则对以上内容进行去AI味润色，直接输出润色后的完整正文。"""

    provider = registry.get_provider(project.ai_provider)

    async def stream():
        full = ""
        try:
            async for chunk in provider.stream_generate(system_prompt, user_prompt):
                full += chunk
                yield {"data": json.dumps({"type": "chunk", "content": chunk}, ensure_ascii=False)}
            chapter.content = full
            chapter.word_count = len(full)
            chapter.status = "polished"
            yield {"data": "[DONE]"}
        except Exception as e:
            yield {"data": json.dumps({"type": "error", "message": str(e)}, ensure_ascii=False)}

    return EventSourceResponse(stream())


@router.post("/{chapter_id}/rewrite")
async def rewrite_chapter(
    chapter_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    chapter = await session.get(Chapter, chapter_id)
    if not chapter:
        raise HTTPException(status_code=404, detail="章节不存在")
    if not chapter.content:
        raise HTTPException(status_code=400, detail="章节无内容可改写")

    project = await _get_project(session, chapter.project_id)
    await _save_version(session, chapter, "before_rewrite")

    system_prompt = rules.build_system_prompt(
        platform=project.target_platform,
        style=project.style_preset,
        genre=project.genre,
    )
    user_prompt = f"""请对以下小说章节进行改写优化，保持情节不变但提升文笔质量。

## 原文
{chapter.content}

请直接输出改写后的完整正文。"""

    provider = registry.get_provider(project.ai_provider)

    async def stream():
        full = ""
        try:
            async for chunk in provider.stream_generate(system_prompt, user_prompt):
                full += chunk
                yield {"data": json.dumps({"type": "chunk", "content": chunk}, ensure_ascii=False)}
            chapter.content = full
            chapter.word_count = len(full)
            chapter.status = "edited"
            yield {"data": "[DONE]"}
        except Exception as e:
            yield {"data": json.dumps({"type": "error", "message": str(e)}, ensure_ascii=False)}

    return EventSourceResponse(stream())


@router.post("/{chapter_id}/continue")
async def continue_chapter(
    chapter_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    chapter = await session.get(Chapter, chapter_id)
    if not chapter:
        raise HTTPException(status_code=404, detail="章节不存在")
    if not chapter.content:
        raise HTTPException(status_code=400, detail="章节无内容可续写")

    project = await _get_project(session, chapter.project_id)
    await _save_version(session, chapter, "before_expand")

    system_prompt = rules.build_system_prompt(
        platform=project.target_platform,
        style=project.style_preset,
        genre=project.genre,
    )
    remaining = max(0, (chapter.word_target or 3000) - len(chapter.content))
    target = max(500, remaining)

    user_prompt = f"""请续写以下小说章节，目标续写约 {target} 字。

## 已有内容（末尾部分）
{chapter.content[-2000:]}

## 章节信息
- 章末钩子：{chapter.chapter_hook or ''}
- 情感基调：{chapter.emotional_tone or ''}

请直接输出续写内容（不要重复已有内容）。"""

    provider = registry.get_provider(project.ai_provider)

    async def stream():
        full = ""
        try:
            async for chunk in provider.stream_generate(system_prompt, user_prompt):
                full += chunk
                yield {"data": json.dumps({"type": "chunk", "content": chunk}, ensure_ascii=False)}
            chapter.content = chapter.content + full
            chapter.word_count = len(chapter.content)
            yield {"data": "[DONE]"}
        except Exception as e:
            yield {"data": json.dumps({"type": "error", "message": str(e)}, ensure_ascii=False)}

    return EventSourceResponse(stream())


@router.get("/{chapter_id}/versions", response_model=list[VersionResponse])
async def get_versions(
    chapter_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    chapter = await session.get(Chapter, chapter_id)
    if not chapter:
        raise HTTPException(status_code=404, detail="章节不存在")

    stmt = (
        select(Version)
        .where(Version.chapter_id == chapter_id)
        .order_by(Version.created_at.desc())
    )
    result = await session.execute(stmt)
    versions = list(result.scalars().all())
    return [VersionResponse.model_validate(v) for v in versions]


@router.post("/{chapter_id}/rollback/{version_id}", response_model=ChapterResponse)
async def rollback_to_version(
    chapter_id: uuid.UUID,
    version_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    chapter = await session.get(Chapter, chapter_id)
    if not chapter:
        raise HTTPException(status_code=404, detail="章节不存在")

    version = await session.get(Version, version_id)
    if not version or version.chapter_id != chapter_id:
        raise HTTPException(status_code=404, detail="版本不存在")

    await _save_version(session, chapter, "before_rollback")
    chapter.content = version.content
    chapter.word_count = len(version.content) if version.content else 0
    chapter.status = "edited"
    await session.flush()
    await session.refresh(chapter)
    return ChapterResponse.model_validate(chapter)


async def _get_project(session: AsyncSession, project_id: uuid.UUID) -> Project:
    stmt = (
        select(Project)
        .where(Project.id == project_id)
        .options(selectinload(Project.characters))
    )
    result = await session.execute(stmt)
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    return project
