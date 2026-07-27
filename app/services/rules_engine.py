from __future__ import annotations

import logging
from pathlib import Path

from app.config import RULES_DIR
from app.core.markdown.parser import read_markdown_content

logger = logging.getLogger(__name__)


class RulesFileNotFound(Exception):
    """Raised when a required rules file is missing."""


class RulesEngine:
    """Loads Markdown rule files and assembles System Prompts.

    Rule files live under RULES_DIR with this structure:
        rules/platforms/{name}.md
        rules/generation/{step}.md
        rules/styles/{name}.md
        rules/genres/{name}.md
    """

    def __init__(self, rules_dir: Path | None = None) -> None:
        self.rules_dir = rules_dir or RULES_DIR

    def _load(self, path: Path, required: bool = True) -> str:
        if not path.exists():
            if required:
                raise RulesFileNotFound(f"必需的规则文件缺失: {path}")
            logger.warning("可选规则文件不存在，跳过: %s", path)
            return ""

        content = read_markdown_content(path)
        if not content.strip():
            if required:
                raise RulesFileNotFound(f"规则文件内容为空: {path}")
            logger.warning("规则文件内容为空，跳过: %s", path)
            return ""

        return content

    def load_platform_rules(self, platform: str) -> str:
        """Load platform rules (required — will raise if missing)."""
        path = self.rules_dir / "platforms" / f"{platform}.md"
        return self._load(path, required=True)

    def load_generation_rules(self, step: str) -> str:
        """Load generation step rules (required)."""
        path = self.rules_dir / "generation" / f"{step}.md"
        return self._load(path, required=True)

    def load_style(self, style: str) -> str:
        """Load style template (optional — returns empty if missing)."""
        path = self.rules_dir / "styles" / f"{style}.md"
        return self._load(path, required=False)

    def load_genre(self, genre: str) -> str:
        """Load genre rules (optional — returns empty if missing)."""
        path = self.rules_dir / "genres" / f"{genre}.md"
        return self._load(path, required=False)

    def build_system_prompt(
        self,
        platform: str,
        style: str | None = None,
        genre: str | None = None,
    ) -> str:
        """Assemble full System Prompt = base + platform + style + genre."""
        parts = [self.load_generation_rules("system-prompt")]
        parts.append(self.load_platform_rules(platform))
        if style:
            style_content = self.load_style(style)
            if style_content:
                parts.append(style_content)
        if genre:
            genre_content = self.load_genre(genre)
            if genre_content:
                parts.append(genre_content)
        return "\n\n".join(parts)

    def build_step_prompt(
        self,
        step: str,
        platform: str,
        style: str | None = None,
        genre: str | None = None,
    ) -> tuple[str, str]:
        """Build system prompt + step-specific generation rules.

        Returns (system_prompt, step_rules) tuple.
        """
        system_prompt = self.build_system_prompt(platform, style, genre)
        step_rules = self.load_generation_rules(step)
        return system_prompt, step_rules

    def list_available(self, category: str) -> list[dict[str, str]]:
        """List available rule files in a category (platforms/styles/genres).

        Returns list of {name, display_name, description}.
        """
        from app.core.markdown.parser import parse_markdown_file

        category_dir = self.rules_dir / category
        if not category_dir.exists():
            return []

        result = []
        for md_file in sorted(category_dir.glob("*.md")):
            if md_file.name == "AGENTS.md":
                continue
            parsed = parse_markdown_file(md_file)
            result.append({
                "name": parsed.name or md_file.stem,
                "display_name": parsed.display_name or md_file.stem,
                "description": parsed.description or "",
            })
        return result
