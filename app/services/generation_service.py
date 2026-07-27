from __future__ import annotations

import json
import logging
import uuid
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ai import registry
from app.models.character import Character
from app.models.outline import Outline
from app.models.project import Project
from app.models.project_setting import ProjectSetting
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
