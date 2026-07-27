from __future__ import annotations

import json
import logging
import uuid

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ai import registry
from app.models.chapter import Chapter
from app.models.narrative_snapshot import NarrativeSnapshot
from app.models.project import Project
from app.services.rules_engine import RulesEngine

logger = logging.getLogger(__name__)
rules = RulesEngine()

SNAPSHOT_PROMPT = """你是一个叙事状态追踪助手。根据本章内容和上一章快照，生成更新后的叙事状态快照。

## 要求
1. 基于上一章快照做增量更新（不是从零开始）
2. 总字数控制在 4000 字以内
3. 严格按照 JSON 格式输出

## 输出 JSON 格式
{
  "characters_state": {"角色名": {"location": "", "emotion": "", "knowledge": "", "goals": "", "status": ""}},
  "plot_hooks": [{"description": "", "setup_chapter": "", "status": "open/resolved", "resolve_chapter": ""}],
  "timeline": [{"chapter": "", "story_time": "", "events": [""]}],
  "items": [{"name": "", "current_holder": "", "location": "", "status": ""}],
  "world_rules": [{"rule": "", "source": ""}]
}"""


async def create_snapshot_after_chapter(
    session: AsyncSession,
    project: Project,
    chapter: Chapter,
) -> NarrativeSnapshot:
    """Create a narrative snapshot after a chapter is generated.

    Reads the previous chapter's snapshot, sends both + new chapter content
    to AI for incremental update, and saves the new snapshot.
    """
    prev_snapshot = await _get_previous_snapshot(session, chapter)

    prev_snapshot_text = ""
    if prev_snapshot:
        prev_snapshot_text = f"""## 上一章快照
角色状态：{json.dumps(prev_snapshot.characters_state or {}, ensure_ascii=False)[:800]}
伏笔追踪：{json.dumps(prev_snapshot.plot_hooks or [], ensure_ascii=False)[:500]}
时间线：{json.dumps(prev_snapshot.timeline or [], ensure_ascii=False)[:300]}
重要物品：{json.dumps(prev_snapshot.items or [], ensure_ascii=False)[:200]}
"""

    chapter_text = (chapter.content or "")[:3000]

    user_prompt = f"""{prev_snapshot_text}

## 本章内容（{chapter.title}）
{chapter_text}

请基于以上信息生成更新后的叙事状态快照，JSON 格式输出。"""

    provider = registry.get_provider(project.ai_provider)
    response = await provider.generate(SNAPSHOT_PROMPT, user_prompt)
    data = _parse_snapshot_json(response)

    existing = await _get_snapshot_for_chapter(session, chapter.id)
    if existing:
        existing.characters_state = data.get("characters_state")
        existing.plot_hooks = data.get("plot_hooks")
        existing.timeline = data.get("timeline")
        existing.items = data.get("items")
        existing.world_rules = data.get("world_rules")
        existing.status = "current"
        return existing

    snapshot = NarrativeSnapshot(
        id=uuid.uuid4(),
        project_id=project.id,
        chapter_id=chapter.id,
        characters_state=data.get("characters_state"),
        plot_hooks=data.get("plot_hooks"),
        timeline=data.get("timeline"),
        items=data.get("items"),
        world_rules=data.get("world_rules"),
        status="current",
    )
    session.add(snapshot)
    return snapshot


async def mark_subsequent_stale(
    session: AsyncSession, chapter: Chapter
) -> int:
    """Mark snapshots of all chapters after this one as stale."""
    stmt = (
        select(Chapter.id)
        .where(
            Chapter.volume_id == chapter.volume_id,
            Chapter.sort_order > chapter.sort_order,
        )
    )
    result = await session.execute(stmt)
    chapter_ids = [row[0] for row in result.all()]

    if not chapter_ids:
        return 0

    update_stmt = (
        update(NarrativeSnapshot)
        .where(NarrativeSnapshot.chapter_id.in_(chapter_ids))
        .values(status="stale")
    )
    result = await session.execute(update_stmt)
    return result.rowcount


async def _get_previous_snapshot(
    session: AsyncSession, chapter: Chapter
) -> NarrativeSnapshot | None:
    stmt = (
        select(NarrativeSnapshot)
        .join(Chapter, NarrativeSnapshot.chapter_id == Chapter.id)
        .where(
            Chapter.volume_id == chapter.volume_id,
            Chapter.sort_order < chapter.sort_order,
        )
        .order_by(Chapter.sort_order.desc())
        .limit(1)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def _get_snapshot_for_chapter(
    session: AsyncSession, chapter_id: uuid.UUID
) -> NarrativeSnapshot | None:
    stmt = select(NarrativeSnapshot).where(NarrativeSnapshot.chapter_id == chapter_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


def _parse_snapshot_json(content: str) -> dict:
    text = content.strip()
    if "```json" in text:
        text = text.split("```json", 1)[1].split("```", 1)[0]
    elif "```" in text:
        text = text.split("```", 1)[1].split("```", 1)[0]
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        logger.warning("Failed to parse snapshot JSON, returning empty")
        return {}
