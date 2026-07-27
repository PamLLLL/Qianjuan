from __future__ import annotations

import json
import uuid
from unittest.mock import AsyncMock, patch

import pytest

from app.models.chapter import Chapter
from app.models.project import Project
from app.models.volume import Volume


@pytest.fixture
async def project_with_chapter(db_session):
    """Create a project with one volume and one chapter with content."""
    project = Project(
        id=uuid.uuid4(),
        name="编辑测试",
        genre="xuanhuan",
        concept="测试概念",
        target_words=100000,
        target_platform="fanqie",
    )
    db_session.add(project)
    await db_session.flush()

    volume = Volume(
        id=uuid.uuid4(),
        project_id=project.id,
        title="第一卷",
        word_target=50000,
        sort_order=0,
    )
    db_session.add(volume)
    await db_session.flush()

    chapter = Chapter(
        id=uuid.uuid4(),
        project_id=project.id,
        volume_id=volume.id,
        title="第一章 测试",
        summary="测试章节",
        content="这是一段测试正文内容，用于验证编辑功能。",
        word_count=18,
        word_target=3000,
        sort_order=0,
        status="generated",
    )
    db_session.add(chapter)
    await db_session.flush()
    await db_session.commit()
    return project, volume, chapter


@pytest.mark.asyncio
async def test_update_content(client, project_with_chapter):
    _, _, chapter = project_with_chapter
    new_content = "这是手动编辑后的内容，经过了修改。"

    res = await client.put(
        f"/api/chapters/{chapter.id}/content",
        json={"content": new_content},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["content"] == new_content
    assert body["word_count"] == len(new_content)
    assert body["status"] == "edited"


@pytest.mark.asyncio
async def test_update_word_target(client, project_with_chapter):
    _, _, chapter = project_with_chapter

    res = await client.put(
        f"/api/chapters/{chapter.id}/word-target",
        json={"word_target": 5000},
    )
    assert res.status_code == 200
    assert res.json()["word_target"] == 5000


@pytest.mark.asyncio
async def test_get_versions_empty(client, project_with_chapter):
    _, _, chapter = project_with_chapter

    res = await client.get(f"/api/chapters/{chapter.id}/versions")
    assert res.status_code == 200
    assert res.json() == []


@pytest.mark.asyncio
async def test_versions_created_on_edit(client, project_with_chapter):
    _, _, chapter = project_with_chapter

    await client.put(
        f"/api/chapters/{chapter.id}/content",
        json={"content": "第一次编辑"},
    )
    await client.put(
        f"/api/chapters/{chapter.id}/content",
        json={"content": "第二次编辑"},
    )

    res = await client.get(f"/api/chapters/{chapter.id}/versions")
    assert res.status_code == 200
    versions = res.json()
    assert len(versions) == 2


@pytest.mark.asyncio
async def test_rollback_to_version(client, project_with_chapter):
    _, _, chapter = project_with_chapter
    original_content = chapter.content

    await client.put(
        f"/api/chapters/{chapter.id}/content",
        json={"content": "已修改的内容"},
    )

    res = await client.get(f"/api/chapters/{chapter.id}/versions")
    version_id = res.json()[0]["id"]

    res = await client.post(f"/api/chapters/{chapter.id}/rollback/{version_id}")
    assert res.status_code == 200
    assert res.json()["content"] == original_content


@pytest.mark.asyncio
async def test_chapter_not_found(client):
    fake_id = uuid.uuid4()
    res = await client.put(
        f"/api/chapters/{fake_id}/content",
        json={"content": "test"},
    )
    assert res.status_code == 404
