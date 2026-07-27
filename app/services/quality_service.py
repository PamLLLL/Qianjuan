from __future__ import annotations

import json
import logging
import uuid
from collections.abc import AsyncGenerator

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.ai import registry
from app.models.chapter import Chapter
from app.models.project import Project
from app.models.quality_issue import QualityIssue
from app.models.quality_report import QualityReport
from app.services.rules_engine import RulesEngine

logger = logging.getLogger(__name__)
rules = RulesEngine()


async def run_quality_check(
    session: AsyncSession, project: Project
) -> AsyncGenerator[str, None]:
    """Run full quality check on project (F16). Streams then saves report."""
    system_prompt = rules.build_system_prompt(
        platform=project.target_platform,
        style=project.style_preset,
        genre=project.genre,
    )
    check_rules = rules.load_generation_rules("quality-check")

    chapters = await _get_all_chapters_with_content(session, project.id)
    if not chapters:
        yield json.dumps({"type": "error", "message": "没有已生成的章节内容"})
        return

    chapter_summaries = []
    for ch in chapters:
        summary = f"【{ch.title}】{(ch.summary or '')[:100]}"
        if ch.content:
            summary += f"\n正文片段：{ch.content[:500]}"
        chapter_summaries.append(summary)

    char_ctx = ""
    if project.characters:
        chars = "\n".join(
            f"- {c.name}({c.role}): {(c.personality or '')[:80]}"
            for c in project.characters[:8]
        )
        char_ctx = f"\n## 角色设定\n{chars}"

    user_prompt = f"""{check_rules}

## 项目信息
- 小说类型：{project.genre}
- 目标平台：{project.target_platform}
{char_ctx}

## 章节内容（共 {len(chapters)} 章）
{chr(10).join(chapter_summaries)}

请对以上内容进行全面质量检测，按 JSON 格式输出检测结果。"""

    provider = registry.get_provider(project.ai_provider)
    full_content = ""

    async for chunk in provider.stream_generate(system_prompt, user_prompt):
        full_content += chunk
        yield chunk

    await _save_quality_report(session, project, chapters, full_content)


async def suggest_fix(
    session: AsyncSession, issue: QualityIssue, project: Project
) -> str:
    """Generate a fix suggestion for a quality issue."""
    if not issue.chapter_id:
        return "无法定位到具体章节"

    chapter = await session.get(Chapter, issue.chapter_id)
    if not chapter or not chapter.content:
        return "章节内容为空"

    system_prompt = rules.build_system_prompt(
        platform=project.target_platform,
        style=project.style_preset,
        genre=project.genre,
    )

    user_prompt = f"""请修复以下小说质量问题。

## 问题信息
- 类别：{issue.category}
- 严重程度：{issue.severity}
- 问题描述：{issue.description}
- 原文片段：{issue.original_text or '无'}
- AI 建议：{issue.suggestion or '无'}

## 章节上下文
章节：{chapter.title}
相关内容：{chapter.content[:2000]}

请直接输出修复后的文本片段（只输出需要替换的部分，不要输出整章内容）。"""

    provider = registry.get_provider(project.ai_provider)
    fix_content = await provider.generate(system_prompt, user_prompt)

    issue.fix_content = fix_content
    issue.fix_status = "suggested"
    return fix_content


async def apply_fix(session: AsyncSession, issue: QualityIssue) -> bool:
    """Apply a confirmed fix to the chapter content."""
    if not issue.fix_content or not issue.chapter_id:
        return False

    chapter = await session.get(Chapter, issue.chapter_id)
    if not chapter or not chapter.content:
        return False

    if issue.original_text and issue.original_text in chapter.content:
        chapter.content = chapter.content.replace(issue.original_text, issue.fix_content, 1)
        chapter.word_count = len(chapter.content)
    else:
        logger.warning("Original text not found in chapter, appending fix note")

    issue.fix_status = "applied"
    return True


async def _get_all_chapters_with_content(
    session: AsyncSession, project_id: uuid.UUID
) -> list[Chapter]:
    stmt = (
        select(Chapter)
        .where(Chapter.project_id == project_id, Chapter.content.isnot(None))
        .order_by(Chapter.sort_order)
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def _save_quality_report(
    session: AsyncSession,
    project: Project,
    chapters: list[Chapter],
    content: str,
) -> QualityReport:
    data = _parse_quality_json(content)

    report = QualityReport(
        id=uuid.uuid4(),
        project_id=project.id,
        overall_score=data.get("overall_score"),
        strengths=data.get("strengths"),
        summary=data.get("summary"),
    )
    session.add(report)
    await session.flush()

    chapter_map = {ch.title: ch.id for ch in chapters}

    issues = data.get("issues", [])
    for issue_data in issues:
        chapter_title = issue_data.get("chapter_title", "")
        chapter_id = chapter_map.get(chapter_title)

        qi = QualityIssue(
            id=uuid.uuid4(),
            report_id=report.id,
            chapter_id=chapter_id,
            severity=issue_data.get("severity", "info"),
            category=issue_data.get("category", "其他"),
            chapter_title=chapter_title,
            description=issue_data.get("description", ""),
            original_text=issue_data.get("original_text"),
            suggestion=issue_data.get("suggestion"),
            fix_status="pending",
        )
        session.add(qi)

    return report


def _parse_quality_json(content: str) -> dict:
    text = content.strip()
    if "```json" in text:
        text = text.split("```json", 1)[1].split("```", 1)[0]
    elif "```" in text:
        text = text.split("```", 1)[1].split("```", 1)[0]
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        logger.warning("Failed to parse quality check JSON")
        return {"issues": [], "overall_score": 0, "summary": content[:500]}
