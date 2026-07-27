from __future__ import annotations

import pytest
from pathlib import Path

from app.services.rules_engine import RulesEngine, RulesFileNotFound
from app.config import RULES_DIR


@pytest.fixture
def engine():
    return RulesEngine(rules_dir=RULES_DIR)


def test_load_platform_rules(engine):
    content = engine.load_platform_rules("fanqie")
    assert content
    assert "番茄" in content or "fanqie" in content.lower() or len(content) > 0


def test_load_platform_rules_missing(engine):
    with pytest.raises(RulesFileNotFound):
        engine.load_platform_rules("nonexistent_platform")


def test_load_style_optional(engine):
    content = engine.load_style("nonexistent_style")
    assert content == ""


def test_load_genre_optional(engine):
    content = engine.load_genre("nonexistent_genre")
    assert content == ""


def test_load_genre_existing(engine):
    content = engine.load_genre("xuanhuan")
    assert content


def test_load_generation_rules(engine):
    content = engine.load_generation_rules("system-prompt")
    assert content


def test_build_system_prompt(engine):
    prompt = engine.build_system_prompt(platform="fanqie", style="hot-blood", genre="xuanhuan")
    assert len(prompt) > 0


def test_build_system_prompt_no_style_genre(engine):
    prompt = engine.build_system_prompt(platform="fanqie")
    assert len(prompt) > 0


def test_list_available_platforms(engine):
    platforms = engine.list_available("platforms")
    assert len(platforms) == 4
    names = [p["name"] for p in platforms]
    assert "fanqie" in names
    assert "qidian" in names


def test_list_available_genres(engine):
    genres = engine.list_available("genres")
    assert len(genres) == 6


def test_list_available_styles(engine):
    styles = engine.list_available("styles")
    assert len(styles) == 4


def test_list_available_nonexistent(engine):
    result = engine.list_available("nonexistent_category")
    assert result == []
