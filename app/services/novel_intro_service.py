from __future__ import annotations

import json
import logging
import uuid
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ai import registry
from app.models.novel_intro import NovelIntro
from app.models.project import Project
from app.services.rules_engine import RulesEngine

logger = logging.getLogger(__name__)
rules = RulesEngine()


async def generate_novel_intro(
    session: AsyncSession, project: Project
) -> AsyncGenerator[str, None]:
    """Generate novel intro / publishing materials (F25)."""
    system_prompt, step_rules = rules.build_step_prompt(
        step="novel-intro",
        platform=project.target_platform,
        style=project.style_preset,
        genre=project.genre,
    )

    context_parts = [
        f"- 小说类型：{project.genre}",
        f"- 核心创意：{project.concept}",
        f"- 目标平台：{project.target_platform}",
        f"- 目标字数：{project.target_words} 字",
    ]

    if project.setting:
        context_parts.append(f"- 基调：{project.setting.tone or ''}")
        context_parts.append(f"- 核心冲突：{project.setting.core_conflict or ''}")

    if project.characters:
        for c in project.characters[:4]:
            context_parts.append(f"- 角色：{c.name}（{c.role}）— {(c.personality or '')[:60]}")

    if project.outline:
        context_parts.append(f"- 故事前提：{project.outline.premise or ''}")

    user_prompt = f"""{step_rules}

## 项目信息
{chr(10).join(context_parts)}

请生成完整的小说发布素材，严格按照 JSON 格式输出。"""

    provider = registry.get_provider(project.ai_provider)
    full_content = ""

    async for chunk in provider.stream_generate(system_prompt, user_prompt):
        full_content += chunk
        yield chunk

    _save_intro(session, project, full_content)


def _save_intro(session: AsyncSession, project: Project, content: str) -> None:
    data = _parse_json(content)

    intro = NovelIntro(
        id=uuid.uuid4(),
        project_id=project.id,
        title_candidates=data.get("title_candidates"),
        selected_title=None,
        hook_line=data.get("hook_line", ""),
        lead_characters=data.get("lead_characters"),
        cp_line=data.get("cp_line"),
        tags=data.get("tags"),
        synopsis=data.get("synopsis", ""),
    )
    session.add(intro)


def _parse_json(content: str) -> dict:
    text = content.strip()
    if "```json" in text:
        text = text.split("```json", 1)[1].split("```", 1)[0]
    elif "```" in text:
        text = text.split("```", 1)[1].split("```", 1)[0]
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        logger.warning("Failed to parse novel intro JSON")
        return {}
