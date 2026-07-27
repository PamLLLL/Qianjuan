from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_create_project(client):
    data = {
        "name": "测试小说",
        "genre": "xuanhuan",
        "concept": "一个穿越修仙的故事",
        "target_words": 200000,
        "target_platform": "fanqie",
    }
    res = await client.post("/api/projects", json=data)
    assert res.status_code == 201
    body = res.json()
    assert body["name"] == "测试小说"
    assert body["genre"] == "xuanhuan"
    assert body["target_platform"] == "fanqie"
    assert body["status"] == "draft"
    assert body["actual_words"] == 0
    assert "id" in body


@pytest.mark.asyncio
async def test_create_project_missing_fields(client):
    res = await client.post("/api/projects", json={"name": "只有名字"})
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_list_projects_empty(client):
    res = await client.get("/api/projects")
    assert res.status_code == 200
    body = res.json()
    assert body["items"] == []
    assert body["total"] == 0
    assert body["page"] == 1


@pytest.mark.asyncio
async def test_list_projects_with_data(client):
    for i in range(3):
        await client.post("/api/projects", json={
            "name": f"小说{i}",
            "genre": "dushi",
            "concept": f"故事{i}",
            "target_words": 100000,
            "target_platform": "qidian",
        })

    res = await client.get("/api/projects?page=1&size=2")
    assert res.status_code == 200
    body = res.json()
    assert len(body["items"]) == 2
    assert body["total"] == 3
    assert body["pages"] == 2


@pytest.mark.asyncio
async def test_get_project(client):
    create_res = await client.post("/api/projects", json={
        "name": "获取测试",
        "genre": "yanqing",
        "concept": "言情故事",
        "target_words": 50000,
        "target_platform": "zhihu",
    })
    project_id = create_res.json()["id"]

    res = await client.get(f"/api/projects/{project_id}")
    assert res.status_code == 200
    assert res.json()["name"] == "获取测试"


@pytest.mark.asyncio
async def test_get_project_not_found(client):
    res = await client.get("/api/projects/00000000-0000-0000-0000-000000000000")
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_update_project(client):
    create_res = await client.post("/api/projects", json={
        "name": "更新测试",
        "genre": "xuanyi",
        "concept": "悬疑故事",
        "target_words": 80000,
        "target_platform": "qimao",
    })
    project_id = create_res.json()["id"]

    res = await client.put(f"/api/projects/{project_id}", json={
        "name": "更新后的名称",
        "status": "generating",
    })
    assert res.status_code == 200
    assert res.json()["name"] == "更新后的名称"
    assert res.json()["status"] == "generating"


@pytest.mark.asyncio
async def test_delete_project(client):
    create_res = await client.post("/api/projects", json={
        "name": "删除测试",
        "genre": "kehuan",
        "concept": "科幻故事",
        "target_words": 60000,
        "target_platform": "fanqie",
    })
    project_id = create_res.json()["id"]

    res = await client.delete(f"/api/projects/{project_id}")
    assert res.status_code == 204

    res = await client.get(f"/api/projects/{project_id}")
    assert res.status_code == 404
