from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

import frontmatter

logger = logging.getLogger(__name__)


@dataclass
class ParsedMarkdown:
    content: str
    metadata: dict = field(default_factory=dict)
    name: str = ""
    type: str = ""
    display_name: str = ""
    description: str = ""
    version: str = ""


def parse_markdown_file(path: str | Path) -> ParsedMarkdown:
    """Parse a Markdown file with YAML frontmatter.

    Tries UTF-8 first, then GBK, then Latin-1.
    If frontmatter is malformed, returns content only with a warning.
    """
    path = Path(path)
    raw = _read_with_fallback_encoding(path)

    try:
        post = frontmatter.loads(raw)
        metadata = dict(post.metadata)
        return ParsedMarkdown(
            content=post.content,
            metadata=metadata,
            name=metadata.get("name", ""),
            type=metadata.get("type", ""),
            display_name=metadata.get("display_name", ""),
            description=metadata.get("description", ""),
            version=str(metadata.get("version", "")),
        )
    except Exception:
        logger.warning("Failed to parse frontmatter in %s, using raw content", path)
        return ParsedMarkdown(content=raw)


def read_markdown_content(path: str | Path) -> str:
    """Read a Markdown file and return only the body content (no frontmatter)."""
    parsed = parse_markdown_file(path)
    return parsed.content


def _read_with_fallback_encoding(path: Path) -> str:
    """Read file with encoding fallback: UTF-8 → GBK → Latin-1."""
    for encoding in ("utf-8", "gbk", "latin-1"):
        try:
            return path.read_text(encoding=encoding)
        except (UnicodeDecodeError, UnicodeError):
            continue
    raise ValueError(f"Cannot decode file {path} with any supported encoding")
