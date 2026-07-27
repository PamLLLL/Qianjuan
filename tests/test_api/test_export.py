from __future__ import annotations

import uuid

import pytest

from app.models.chapter import Chapter
from app.models.project import Project
from app.models.volume import Volume


@pytest.fixture
async def exportable_project(db_session):
    """Project with chapters that have content, ready for export."""
    project = Project(
        id=uuid.uuid4(),
        name="导出测试小说",
        genre="xuanhuan",
        concept="测试导出",
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

    for i in range(3):
        ch = Chapter(
            id=uuid.uuid4(),
            project_id=project.id,
            volume_id=volume.id,
            title=f"第{i+1}章 测试章节",
            content=f"这是第{i+1}章的正文内容。" * 50,
            word_count=500,
            word_target=3000,
            sort_order=i,
            status="generated",
        )
        db_session.add(ch)

    await db_session.flush()
    await db_session.commit()
    return project, volume


@pytest.mark.asyncio
async def test_export_txt(client, exportable_project):
    project, _ = exportable_project
    res = await client.post(
        f"/api/export/{project.id}",
        json={"format": "txt", "scope": "all"},
    )
    assert res.status_code == 200
    assert "text/plain" in res.headers.get("content-type", "")
    content = res.text
    assert "导出测试小说" in content
    assert "第1章" in content


@pytest.mark.asyncio
async def test_export_docx(client, exportable_project):
    project, _ = exportable_project
    res = await client.post(
        f"/api/export/{project.id}",
        json={"format": "docx", "scope": "all"},
    )
    assert res.status_code == 200
    assert len(res.content) > 0


@pytest.mark.asyncio
async def test_export_epub(client, exportable_project):
    project, _ = exportable_project
    res = await client.post(
        f"/api/export/{project.id}",
        json={"format": "epub", "scope": "all"},
    )
    assert res.status_code == 200
    assert len(res.content) > 0


@pytest.mark.asyncio
async def test_export_volume_scope(client, exportable_project):
    project, volume = exportable_project
    res = await client.post(
        f"/api/export/{project.id}",
        json={"format": "txt", "scope": "volume", "volume_id": str(volume.id)},
    )
    assert res.status_code == 200


@pytest.mark.asyncio
async def test_export_no_content(client):
    create_res = await client.post("/api/projects", json={
        "name": "空项目",
        "genre": "dushi",
        "concept": "空的",
        "target_words": 50000,
        "target_platform": "qidian",
    })
    project_id = create_res.json()["id"]

    res = await client.post(
        f"/api/export/{project_id}",
        json={"format": "txt", "scope": "all"},
    )
    assert res.status_code == 400


@pytest.mark.asyncio
async def test_export_invalid_format(client, exportable_project):
    project, _ = exportable_project
    res = await client.post(
        f"/api/export/{project.id}",
        json={"format": "pdf", "scope": "all"},
    )
    assert res.status_code == 422
