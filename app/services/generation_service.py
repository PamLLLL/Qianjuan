from __future__ import annotations

import json
import logging
import uuid
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.ai import registry
from app.models.chapter import Chapter
from app.models.character import Character
from app.models.narrative_snapshot import NarrativeSnapshot
from app.models.outline import Outline
from app.models.project import Project
from app.models.project_setting import ProjectSetting
from app.models.volume import Volume
from app.models.worldview import Worldview
from app.services.rules_engine import RulesEngine

logger = logging.getLogger(__name__)
rules = RulesEngine()


async def generate_settings(
    session: AsyncSession, project: Project
) -> AsyncGenerator[str, None]:
    """Generate basic story settings (F03). Streams chunks then saves."""
    system_prompt, step_rules = rules.build_step_prompt(
        step="settings",
        platform=project.target_platform,
        style=project.style_preset,
        genre=project.genre,
    )

    user_prompt = f"""{step_rules}

## 用户输入
- 小说类型：{project.genre}
- 核心创意：{project.concept}
- 目标字数：{project.target_words} 字
- 目标平台：{project.target_platform}
{f'- 自定义风格：{project.custom_style}' if project.custom_style else ''}

请根据以上信息生成基础设定，严格按照 JSON 格式输出。"""

    provider = registry.get_provider(project.ai_provider)
    full_content = ""

    async for chunk in provider.stream_generate(system_prompt, user_prompt):
        full_content += chunk
        yield chunk

    _save_settings(session, project, full_content)


def _save_settings(session: AsyncSession, project: Project, content: str) -> None:
    data = _parse_json(content)
    setting = ProjectSetting(
        id=uuid.uuid4(),
        project_id=project.id,
        title_suggestions=data.get("title_suggestions"),
        background=data.get("background", ""),
        tone=data.get("tone", ""),
        core_conflict=data.get("core_conflict", ""),
        themes=data.get("themes"),
        target_audience=data.get("target_audience", ""),
        unique_selling_point=data.get("unique_selling_point", ""),
    )
    session.add(setting)


async def generate_characters(
    session: AsyncSession, project: Project
) -> AsyncGenerator[str, None]:
    """Generate character system (F04). Streams chunks then saves."""
    system_prompt, step_rules = rules.build_step_prompt(
        step="characters",
        platform=project.target_platform,
        style=project.style_preset,
        genre=project.genre,
    )

    setting_ctx = ""
    if project.setting:
        setting_ctx = f"""
## 已有设定
- 背景：{project.setting.background or ''}
- 基调：{project.setting.tone or ''}
- 核心冲突：{project.setting.core_conflict or ''}
"""

    user_prompt = f"""{step_rules}

## 用户输入
- 小说类型：{project.genre}
- 核心创意：{project.concept}
- 目标字数：{project.target_words} 字
{setting_ctx}

请生成完整的人物体系，严格按照 JSON 数组格式输出。"""

    provider = registry.get_provider(project.ai_provider)
    full_content = ""

    async for chunk in provider.stream_generate(system_prompt, user_prompt):
        full_content += chunk
        yield chunk

    _save_characters(session, project, full_content)


def _save_characters(session: AsyncSession, project: Project, content: str) -> None:
    data = _parse_json(content)
    characters = data if isinstance(data, list) else data.get("characters", [])

    for i, char in enumerate(characters):
        c = Character(
            id=uuid.uuid4(),
            project_id=project.id,
            name=char.get("name", f"角色{i+1}"),
            role=char.get("role", "supporting"),
            personality=char.get("personality", ""),
            background=char.get("background", ""),
            appearance=char.get("appearance", ""),
            motivation=char.get("motivation", ""),
            arc=char.get("arc", ""),
            relationships=char.get("relationships"),
            sort_order=i,
        )
        session.add(c)


async def generate_worldview(
    session: AsyncSession, project: Project
) -> AsyncGenerator[str, None]:
    """Generate worldview (F05). Streams chunks then saves."""
    system_prompt, step_rules = rules.build_step_prompt(
        step="worldview",
        platform=project.target_platform,
        style=project.style_preset,
        genre=project.genre,
    )

    setting_ctx = ""
    if project.setting:
        setting_ctx = f"- 背景：{project.setting.background or ''}\n"

    user_prompt = f"""{step_rules}

## 用户输入
- 小说类型：{project.genre}
- 核心创意：{project.concept}
{setting_ctx}

请生成完整的世界观设定，严格按照 JSON 格式输出。"""

    provider = registry.get_provider(project.ai_provider)
    full_content = ""

    async for chunk in provider.stream_generate(system_prompt, user_prompt):
        full_content += chunk
        yield chunk

    _save_worldview(session, project, full_content)


def _save_worldview(session: AsyncSession, project: Project, content: str) -> None:
    data = _parse_json(content)
    wv = Worldview(
        id=uuid.uuid4(),
        project_id=project.id,
        world_type=data.get("world_type", ""),
        geography=data.get("geography", ""),
        society=data.get("society", ""),
        power_system=data.get("power_system", ""),
        history=data.get("history", ""),
        rules=data.get("rules"),
        culture=data.get("culture", ""),
        technology=data.get("technology", ""),
    )
    session.add(wv)


async def generate_outline(
    session: AsyncSession, project: Project
) -> AsyncGenerator[str, None]:
    """Generate story outline (F06). Streams chunks then saves."""
    system_prompt, step_rules = rules.build_step_prompt(
        step="outline",
        platform=project.target_platform,
        style=project.style_preset,
        genre=project.genre,
    )

    context_parts = [f"- 小说类型：{project.genre}", f"- 核心创意：{project.concept}"]
    if project.setting:
        context_parts.append(f"- 核心冲突：{project.setting.core_conflict or ''}")
    if project.characters:
        char_names = ", ".join(c.name for c in project.characters[:5])
        context_parts.append(f"- 主要角色：{char_names}")

    user_prompt = f"""{step_rules}

## 用户输入
{chr(10).join(context_parts)}
- 目标字数：{project.target_words} 字

请生成三幕结构故事大纲，严格按照 JSON 格式输出。"""

    provider = registry.get_provider(project.ai_provider)
    full_content = ""

    async for chunk in provider.stream_generate(system_prompt, user_prompt):
        full_content += chunk
        yield chunk

    _save_outline(session, project, full_content)


def _save_outline(session: AsyncSession, project: Project, content: str) -> None:
    data = _parse_json(content)
    outline = Outline(
        id=uuid.uuid4(),
        project_id=project.id,
        premise=data.get("premise", ""),
        act_one=data.get("act_one"),
        act_two=data.get("act_two"),
        act_three=data.get("act_three"),
        subplots=data.get("subplots"),
        foreshadowing=data.get("foreshadowing"),
    )
    session.add(outline)


async def generate_volumes(
    session: AsyncSession, project: Project
) -> AsyncGenerator[str, None]:
    """Generate volume structure (F07). Streams chunks then saves."""
    system_prompt, step_rules = rules.build_step_prompt(
        step="outline",
        platform=project.target_platform,
        style=project.style_preset,
        genre=project.genre,
    )

    outline_ctx = ""
    if project.outline:
        outline_ctx = f"- 故事前提：{project.outline.premise or ''}\n"
        if project.outline.act_one:
            outline_ctx += f"- 第一幕：{json.dumps(project.outline.act_one, ensure_ascii=False)}\n"
        if project.outline.act_two:
            outline_ctx += f"- 第二幕：{json.dumps(project.outline.act_two, ensure_ascii=False)}\n"
        if project.outline.act_three:
            outline_ctx += f"- 第三幕：{json.dumps(project.outline.act_three, ensure_ascii=False)}\n"

    user_prompt = f"""{step_rules}

## 任务：生成分卷结构

## 已有信息
- 目标总字数：{project.target_words} 字
{outline_ctx}

## 输出要求
根据故事大纲和目标字数，将故事合理分卷。输出 JSON 数组，每卷包含：
- title: 卷名（如"第一卷 命运之始"）
- summary: 本卷概述（300字+，含关键事件和角色变化）
- word_target: 目标字数
- key_arc: 主要发展弧线
- start_state: 卷开始时角色状态
- end_state: 卷结束时状态变化

请严格按照 JSON 数组格式输出。"""

    provider = registry.get_provider(project.ai_provider)
    full_content = ""

    async for chunk in provider.stream_generate(system_prompt, user_prompt):
        full_content += chunk
        yield chunk

    _save_volumes(session, project, full_content)


def _save_volumes(session: AsyncSession, project: Project, content: str) -> None:
    data = _parse_json(content)
    volumes = data if isinstance(data, list) else data.get("volumes", [])

    for i, vol in enumerate(volumes):
        v = Volume(
            id=uuid.uuid4(),
            project_id=project.id,
            title=vol.get("title", f"第{i+1}卷"),
            summary=vol.get("summary", ""),
            word_target=vol.get("word_target", 0),
            key_arc=vol.get("key_arc", ""),
            start_state=vol.get("start_state", ""),
            end_state=vol.get("end_state", ""),
            sort_order=i,
        )
        session.add(v)


async def generate_chapter_outlines(
    session: AsyncSession, project: Project, volume: Volume
) -> AsyncGenerator[str, None]:
    """Generate chapter outlines for a volume (F08). Streams then saves."""
    system_prompt, step_rules = rules.build_step_prompt(
        step="outline",
        platform=project.target_platform,
        style=project.style_preset,
        genre=project.genre,
    )

    char_ctx = ""
    if project.characters:
        char_ctx = "- 主要角色：" + ", ".join(c.name for c in project.characters[:6]) + "\n"

    user_prompt = f"""{step_rules}

## 任务：为本卷生成章节大纲

## 本卷信息
- 卷名：{volume.title}
- 本卷概述：{volume.summary or ''}
- 目标字数：{volume.word_target} 字
- 主要弧线：{volume.key_arc or ''}
{char_ctx}

## 输出要求
根据本卷目标字数，按每章约 3000 字计算章节数量。输出 JSON 数组，每章包含：
- title: 章节标题
- summary: 章节摘要（100-200字）
- characters_involved: 出场人物名字列表
- emotional_tone: 情感基调
- chapter_hook: 章末钩子描述

请严格按照 JSON 数组格式输出。"""

    provider = registry.get_provider(project.ai_provider)
    full_content = ""

    async for chunk in provider.stream_generate(system_prompt, user_prompt):
        full_content += chunk
        yield chunk

    _save_chapter_outlines(session, project, volume, full_content)


def _save_chapter_outlines(
    session: AsyncSession, project: Project, volume: Volume, content: str
) -> None:
    data = _parse_json(content)
    chapters = data if isinstance(data, list) else data.get("chapters", [])
    chapter_word_target = volume.word_target // max(len(chapters), 1) if chapters else 3000

    for i, ch in enumerate(chapters):
        c = Chapter(
            id=uuid.uuid4(),
            project_id=project.id,
            volume_id=volume.id,
            title=ch.get("title", f"第{i+1}章"),
            summary=ch.get("summary", ""),
            characters_involved=ch.get("characters_involved"),
            emotional_tone=ch.get("emotional_tone", ""),
            chapter_hook=ch.get("chapter_hook", ""),
            word_target=ch.get("word_target", chapter_word_target),
            sort_order=i,
        )
        session.add(c)


async def generate_chapter_content(
    session: AsyncSession,
    project: Project,
    chapter: Chapter,
    word_target: int | None = None,
) -> AsyncGenerator[str, None]:
    """Generate chapter content (F09) with context management per PRD Section 8.

    Context budget ~10500 tokens:
      - System Prompt (platform+style+genre): ~2000
      - Chapter outline + target: ~200
      - Character profiles (involved only): ~1500
      - Worldview: ~1000
      - Last 2-3 chapter summaries: ~500
      - Previous chapter ending (last 1500 chars): ~800
      - Narrative snapshot: ~2000
      - Generation rules: ~1500
    """
    target = word_target or chapter.word_target or 3000
    system_prompt = rules.build_system_prompt(
        platform=project.target_platform,
        style=project.style_preset,
        genre=project.genre,
    )
    step_rules = rules.load_generation_rules("chapter-content")

    context = await _build_chapter_context(session, project, chapter)

    user_prompt = f"""{step_rules}

{context}

## 本章任务
- 章节标题：{chapter.title}
- 章节摘要：{chapter.summary or ''}
- 情感基调：{chapter.emotional_tone or ''}
- 章末钩子：{chapter.chapter_hook or ''}
- 目标字数：{target} 字（允许±10%浮动）

请直接输出小说正文，不要 JSON 包装，不要标注章节标题。"""

    provider = registry.get_provider(project.ai_provider)
    full_content = ""

    async for chunk in provider.stream_generate(system_prompt, user_prompt):
        full_content += chunk
        yield chunk

    chapter.content = full_content
    chapter.word_count = len(full_content)
    chapter.ai_provider = provider.provider_name
    chapter.ai_model = provider.model
    chapter.status = "generated"

    project.actual_words = await _calc_total_words(session, project.id)


async def _build_chapter_context(
    session: AsyncSession, project: Project, chapter: Chapter
) -> str:
    """Build context string for chapter generation (~8000 tokens budget)."""
    parts = []

    # 1. Involved character profiles (精简版)
    if chapter.characters_involved:
        involved_names = set(chapter.characters_involved)
        chars = [c for c in project.characters if c.name in involved_names]
    else:
        chars = project.characters[:5]

    if chars:
        char_lines = []
        for c in chars:
            char_lines.append(
                f"【{c.role}】{c.name}：{(c.personality or '')[:100]}。"
                f"背景：{(c.background or '')[:100]}"
            )
        parts.append("## 出场人物\n" + "\n".join(char_lines))

    # 2. Worldview (全文，通常 <2000 字)
    if project.worldview:
        wv = project.worldview
        wv_text = f"类型：{wv.world_type or ''}\n"
        if wv.power_system:
            wv_text += f"力量体系：{wv.power_system[:300]}\n"
        if wv.society:
            wv_text += f"社会结构：{wv.society[:200]}\n"
        parts.append("## 世界观\n" + wv_text)

    # 3. Recent chapter summaries (最近 2-3 章)
    prev_chapters = await _get_previous_chapters(session, chapter, limit=3)
    if prev_chapters:
        summary_lines = []
        for pc in prev_chapters:
            summary_lines.append(f"- {pc.title}：{(pc.summary or '')[:150]}")
        parts.append("## 前情提要\n" + "\n".join(summary_lines))

    # 4. Previous chapter ending (末尾 1500 字)
    if prev_chapters:
        last_ch = prev_chapters[-1]
        if last_ch.content:
            ending = last_ch.content[-1500:]
            parts.append(f"## 上一章结尾\n{ending}")

    # 5. Narrative snapshot
    if prev_chapters:
        last_ch = prev_chapters[-1]
        snapshot = await _get_snapshot(session, last_ch.id)
        if snapshot:
            snap_parts = []
            if snapshot.characters_state:
                snap_parts.append(f"角色状态：{json.dumps(snapshot.characters_state, ensure_ascii=False)[:800]}")
            if snapshot.plot_hooks:
                snap_parts.append(f"伏笔追踪：{json.dumps(snapshot.plot_hooks, ensure_ascii=False)[:500]}")
            if snapshot.timeline:
                snap_parts.append(f"时间线：{json.dumps(snapshot.timeline, ensure_ascii=False)[:300]}")
            if snap_parts:
                parts.append("## 叙事状态\n" + "\n".join(snap_parts))

    return "\n\n".join(parts)


async def _get_previous_chapters(
    session: AsyncSession, chapter: Chapter, limit: int = 3
) -> list[Chapter]:
    stmt = (
        select(Chapter)
        .where(
            Chapter.volume_id == chapter.volume_id,
            Chapter.sort_order < chapter.sort_order,
            Chapter.content.isnot(None),
        )
        .order_by(Chapter.sort_order.desc())
        .limit(limit)
    )
    result = await session.execute(stmt)
    chapters = list(result.scalars().all())
    chapters.reverse()
    return chapters


async def _get_snapshot(
    session: AsyncSession, chapter_id: uuid.UUID
) -> NarrativeSnapshot | None:
    stmt = select(NarrativeSnapshot).where(NarrativeSnapshot.chapter_id == chapter_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def _calc_total_words(session: AsyncSession, project_id: uuid.UUID) -> int:
    from sqlalchemy import func as sa_func
    stmt = (
        select(sa_func.coalesce(sa_func.sum(Chapter.word_count), 0))
        .where(Chapter.project_id == project_id)
    )
    result = await session.execute(stmt)
    return result.scalar() or 0


def _parse_json(content: str) -> dict | list:
    """Extract JSON from AI response, handling markdown code blocks."""
    text = content.strip()
    if "```json" in text:
        text = text.split("```json", 1)[1]
        text = text.split("```", 1)[0]
    elif "```" in text:
        text = text.split("```", 1)[1]
        text = text.split("```", 1)[0]
    text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        logger.warning("Failed to parse JSON from AI response, returning as raw dict")
        return {"raw_content": content}
