"""
Task REST API — 任务创建、查询、文件访问、删除
"""

import asyncio
import logging
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, HTTPException

from app.config import get_settings
from app.core.orchestrator import AgentOrchestrator
from app.models.task import (
    FileInfo,
    TaskCreateRequest,
    TaskCreateResponse,
    TaskStatus,
    generate_task_id,
)
from app.services.task_store import TaskRecord, get_task_store
from app.services.workspace import WorkspaceManager

logger = logging.getLogger(__name__)

router = APIRouter()
store = get_task_store()
workspace = WorkspaceManager()


@router.post("/task/create", response_model=TaskCreateResponse, status_code=201)
async def create_task(req: TaskCreateRequest, background: BackgroundTasks):
    """
    创建编程任务并后台执行

    流程:
      1. 生成 task_id
      2. 存入 TaskStore
      3. 后台启动 Orchestrator
      4. 立即返回 task_id（不等待执行完成）
    """
    task_id = generate_task_id()
    logger.info(f"Creating task {task_id}: {req.request[:80]}...")

    record = await store.create(task_id, req.request, req.provider)
    record.status = "planning"
    record.is_running = True

    # 后台执行 Agent 流水线
    background.add_task(_run_agent_pipeline, task_id, req.request, req.provider)

    return TaskCreateResponse(
        task_id=task_id,
        status="planning",
        created_at=record.created_at,
    )


@router.get("/task/{task_id}", response_model=TaskStatus)
async def get_task(task_id: str):
    """查询任务状态和执行结果"""
    record = await store.get(task_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")

    return TaskStatus(
        task_id=record.task_id,
        status=record.status,
        plan={
            "task_summary": record.plan_summary or "",
            "steps": record.steps,
        } if record.plan_summary else None,
        files_created=record.files_created,
        files_modified=record.files_modified,
        final_report=record.final_report,
        error_message=record.error_message,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


@router.get("/task/{task_id}/files", response_model=list[str])
async def list_task_files(task_id: str):
    """列出任务生成的所有文件"""
    record = await store.get(task_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")
    return workspace.list_files(task_id)


@router.get("/task/{task_id}/file/{path:path}", response_model=FileInfo)
async def get_task_file(task_id: str, path: str):
    """获取任务生成的单个文件内容"""
    record = await store.get(task_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")

    try:
        content = workspace.read_file(task_id, path)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"File not found: {path}")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    from app.tools.base import detect_language

    return FileInfo(
        path=path,
        content=content,
        size_bytes=len(content.encode("utf-8")),
        language=detect_language(path),
    )


@router.delete("/task/{task_id}")
async def delete_task(task_id: str):
    """删除任务及其工作区"""
    record = await store.get(task_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")

    workspace.cleanup(task_id)
    await store.delete(task_id)

    return {"message": f"Task {task_id} deleted"}


@router.get("/tasks", response_model=list[TaskStatus])
async def list_tasks():
    """列出所有任务"""
    records = await store.list_all()
    return [
        TaskStatus(
            task_id=r.task_id,
            status=r.status,
            files_created=r.files_created,
            files_modified=r.files_modified,
            final_report=r.final_report,
            error_message=r.error_message,
            created_at=r.created_at,
            updated_at=r.updated_at,
        )
        for r in sorted(records, key=lambda r: r.created_at, reverse=True)
    ]


# ── 后台任务 ──────────────────────────────────

async def _run_agent_pipeline(task_id: str, request: str, provider: str):
    """
    后台执行 Agent 流水线

    此函数在 BackgroundTasks 中运行：
      - 不影响 API 响应速度
      - 结果通过 EventBus 推送给 WebSocket
      - 执行完毕后更新 TaskStore
    """
    store = get_task_store()
    wm = WorkspaceManager()

    try:
        orchestrator = AgentOrchestrator(workspace=wm)

        # 运行流水线
        result = await orchestrator.run(
            task_id=task_id,
            user_request=request,
            provider=provider,
        )

        # 同步结果到 TaskStore
        await store.update(
            task_id,
            status=result.get("status", "done"),
            plan_summary=result.get("plan_summary", ""),
            steps=result.get("steps", []),
            files_created=result.get("files_created", []),
            files_modified=result.get("files_modified", []),
            final_report=result.get("final_report", ""),
            error_message=result.get("error_message"),
            is_running=False,
        )

        logger.info(f"Task {task_id} completed: {result.get('status')}")

    except Exception as e:
        logger.exception(f"Task {task_id} failed")
        await store.update(
            task_id,
            status="failed",
            error_message=str(e),
            is_running=False,
        )
