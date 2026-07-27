from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest


MOCK_SETTINGS_JSON = json.dumps({
    "title_suggestions": ["测试书名1", "测试书名2"],
    "background": "一个现代都市修仙世界",
    "tone": "热血励志",
    "core_conflict": "主角逆天改命",
    "themes": ["成长", "友情"],
    "target_audience": "18-30岁男性读者",
    "unique_selling_point": "科学与修仙结合",
})

MOCK_CHARACTERS_JSON = json.dumps([
    {
        "name": "林远",
        "role": "protagonist",
        "personality": "坚韧不拔",
        "background": "普通大学生穿越",
        "appearance": "身材高大",
        "motivation": "回到现实世界",
        "arc": "从懦弱到勇敢",
        "relationships": [{"target": "苏瑶", "relation": "师姐", "dynamic": "互相欣赏"}],
    }
])

MOCK_WORLDVIEW_JSON = json.dumps({
    "world_type": "修仙世界",
    "geography": "九大洲三大洋",
    "society": "宗门林立",
    "power_system": "练气-筑基-金丹-元婴",
    "history": "万年前仙魔大战",
    "rules": [{"rule": "灵气浓度影响修炼速度", "source": "天地法则"}],
    "culture": "尊师重道",
    "technology": "以灵石为能源",
})

MOCK_OUTLINE_JSON = json.dumps({
    "premise": "现代大学生穿越修仙世界",
    "act_one": {"title": "初入仙门", "summary": "主角穿越并加入宗门", "key_events": ["穿越", "拜师"]},
    "act_two": {"title": "崛起之路", "summary": "主角逐渐展露天赋", "key_events": ["比武大会"]},
    "act_three": {"title": "终极之战", "summary": "主角大战魔族", "climax": "决战"},
    "subplots": [{"name": "感情线", "description": "与师姐的羁绊"}],
    "foreshadowing": [{"setup": "神秘戒指", "payoff": "戒指中藏有前辈遗产"}],
})

MOCK_VOLUMES_JSON = json.dumps([
    {
        "title": "第一卷 仙门初入",
        "summary": "主角穿越到修仙世界并加入天剑宗",
        "word_target": 100000,
        "key_arc": "主角适应新世界",
        "start_state": "普通人",
        "end_state": "练气期修士",
    }
])

MOCK_CHAPTERS_JSON = json.dumps([
    {
        "title": "第一章 穿越",
        "summary": "林远意外穿越到修仙世界",
        "characters_involved": ["林远"],
        "emotional_tone": "惊奇迷茫",
        "chapter_hook": "他发现自己的手指尖竟然冒出了一缕微光",
    },
    {
        "title": "第二章 入门",
        "summary": "林远被天剑宗长老发现",
        "characters_involved": ["林远", "苏瑶"],
        "emotional_tone": "紧张期待",
        "chapter_hook": "长老说他的资质前所未见",
    },
])


async def _mock_stream(content: str):
    for i in range(0, len(content), 50):
        yield content[i:i+50]


def _make_mock_provider(response_content: str):
    provider = AsyncMock()
    provider.provider_name = "mock"
    provider.model = "mock-model"
    provider.stream_generate = lambda *a, **kw: _mock_stream(response_content)
    return provider


@pytest.mark.asyncio
async def test_full_generation_flow(client):
    """P0 integration test: create project → generate steps 1-6."""

    # Step 0: Create project
    res = await client.post("/api/projects", json={
        "name": "P0集成测试",
        "genre": "xuanhuan",
        "concept": "现代大学生穿越修仙世界",
        "target_words": 200000,
        "target_platform": "fanqie",
    })
    assert res.status_code == 201
    project_id = res.json()["id"]

    # Step 1: Generate settings
    mock = _make_mock_provider(MOCK_SETTINGS_JSON)
    with patch("app.services.generation_service.registry.get_provider", return_value=mock):
        res = await client.post(f"/api/generate/settings/{project_id}")
        assert res.status_code == 200

    # Verify settings saved
    res = await client.get(f"/api/projects/{project_id}")
    assert res.status_code == 200

    # Step 2: Generate characters
    mock = _make_mock_provider(MOCK_CHARACTERS_JSON)
    with patch("app.services.generation_service.registry.get_provider", return_value=mock):
        res = await client.post(f"/api/generate/characters/{project_id}")
        assert res.status_code == 200

    # Step 3: Generate worldview
    mock = _make_mock_provider(MOCK_WORLDVIEW_JSON)
    with patch("app.services.generation_service.registry.get_provider", return_value=mock):
        res = await client.post(f"/api/generate/worldview/{project_id}")
        assert res.status_code == 200

    # Step 4: Generate outline
    mock = _make_mock_provider(MOCK_OUTLINE_JSON)
    with patch("app.services.generation_service.registry.get_provider", return_value=mock):
        res = await client.post(f"/api/generate/outline/{project_id}")
        assert res.status_code == 200

    # Step 5: Generate volumes
    mock = _make_mock_provider(MOCK_VOLUMES_JSON)
    with patch("app.services.generation_service.registry.get_provider", return_value=mock):
        res = await client.post(f"/api/generate/volumes/{project_id}")
        assert res.status_code == 200


@pytest.mark.asyncio
async def test_generate_settings_conflict(client):
    """Cannot generate settings twice."""
    res = await client.post("/api/projects", json={
        "name": "冲突测试",
        "genre": "dushi",
        "concept": "都市异能",
        "target_words": 100000,
        "target_platform": "qidian",
    })
    project_id = res.json()["id"]

    mock = _make_mock_provider(MOCK_SETTINGS_JSON)
    with patch("app.services.generation_service.registry.get_provider", return_value=mock):
        res = await client.post(f"/api/generate/settings/{project_id}")
        assert res.status_code == 200

        res = await client.post(f"/api/generate/settings/{project_id}")
        assert res.status_code == 409


@pytest.mark.asyncio
async def test_generate_volumes_requires_outline(client):
    """Volumes generation requires outline to exist first."""
    res = await client.post("/api/projects", json={
        "name": "前置检查测试",
        "genre": "yanqing",
        "concept": "言情故事",
        "target_words": 50000,
        "target_platform": "zhihu",
    })
    project_id = res.json()["id"]

    res = await client.post(f"/api/generate/volumes/{project_id}")
    assert res.status_code == 400
