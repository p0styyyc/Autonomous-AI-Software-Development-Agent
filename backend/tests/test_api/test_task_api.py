"""Task REST API 集成测试"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client():
    """创建异步 HTTP 测试客户端"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.anyio
async def test_create_task(client):
    """测试创建任务"""
    response = await client.post(
        "/api/v1/task/create",
        json={"request": "Create a hello world Python script", "provider": "openai"},
    )
    assert response.status_code == 201
    data = response.json()
    assert "task_id" in data
    assert data["status"] == "planning"


@pytest.mark.anyio
async def test_create_task_minimal(client):
    """测试最简请求"""
    response = await client.post(
        "/api/v1/task/create",
        json={"request": "Create a function"},
    )
    assert response.status_code == 201


@pytest.mark.anyio
async def test_create_task_empty_rejected(client):
    """测试空需求被拒绝"""
    response = await client.post(
        "/api/v1/task/create",
        json={"request": ""},
    )
    assert response.status_code == 422


@pytest.mark.anyio
async def test_create_task_invalid_provider(client):
    """测试非法 provider 被拒绝"""
    response = await client.post(
        "/api/v1/task/create",
        json={"request": "test", "provider": "invalid"},
    )
    assert response.status_code == 422


@pytest.mark.anyio
async def test_get_task_not_found(client):
    """测试查询不存在的任务"""
    response = await client.get("/api/v1/task/nonexistent-id")
    assert response.status_code == 404


@pytest.mark.anyio
async def test_create_and_get_task(client):
    """测试创建后立即查询"""
    create_resp = await client.post(
        "/api/v1/task/create", json={"request": "Test task"}
    )
    task_id = create_resp.json()["task_id"]

    get_resp = await client.get(f"/api/v1/task/{task_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["task_id"] == task_id


@pytest.mark.anyio
async def test_list_tasks(client):
    """测试列出所有任务"""
    await client.post("/api/v1/task/create", json={"request": "T1"})
    await client.post("/api/v1/task/create", json={"request": "T2"})

    response = await client.get("/api/v1/tasks")
    assert response.status_code == 200
    assert len(response.json()) >= 2


@pytest.mark.anyio
async def test_list_files_empty(client):
    """测试空任务的文件列表"""
    create_resp = await client.post(
        "/api/v1/task/create", json={"request": "Test"}
    )
    task_id = create_resp.json()["task_id"]

    response = await client.get(f"/api/v1/task/{task_id}/files")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.anyio
async def test_get_file_not_found(client):
    """测试读取不存在的文件"""
    create_resp = await client.post(
        "/api/v1/task/create", json={"request": "Test"}
    )
    task_id = create_resp.json()["task_id"]

    response = await client.get(f"/api/v1/task/{task_id}/file/nope.py")
    assert response.status_code == 404


@pytest.mark.anyio
async def test_delete_task(client):
    """测试删除任务"""
    create_resp = await client.post(
        "/api/v1/task/create", json={"request": "Test"}
    )
    task_id = create_resp.json()["task_id"]

    del_resp = await client.delete(f"/api/v1/task/{task_id}")
    assert del_resp.status_code == 200

    get_resp = await client.get(f"/api/v1/task/{task_id}")
    assert get_resp.status_code == 404


@pytest.mark.anyio
async def test_delete_nonexistent_task(client):
    """测试删除不存在的任务"""
    response = await client.delete("/api/v1/task/fake-id")
    assert response.status_code == 404


@pytest.mark.anyio
async def test_health_check(client):
    """测试健康检查"""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


@pytest.mark.anyio
async def test_write_and_read_file(client):
    """测试通过 API 写入和读取文件"""
    create_resp = await client.post(
        "/api/v1/task/create", json={"request": "Test file I/O"}
    )
    task_id = create_resp.json()["task_id"]

    # 直接用 workspace 写文件
    from app.services.workspace import WorkspaceManager
    wm = WorkspaceManager()
    wm.write_file(task_id, "hello.py", "print('hello world')")

    # 通过 API 读取
    response = await client.get(f"/api/v1/task/{task_id}/file/hello.py")
    assert response.status_code == 200
    data = response.json()
    assert data["content"] == "print('hello world')"
    assert data["language"] == "python"
