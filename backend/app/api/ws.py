"""
WebSocket API — 实时推送 Agent 执行事件

连接: ws://localhost:8000/api/v1/task/{task_id}/stream

事件格式:
  {
    "type": "planning_completed",
    "data": {"task_summary": "...", "steps_count": 3},
    "timestamp": "2026-07-19T10:00:05Z"
  }
"""

import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.event_bus import get_event_bus
from app.services.task_store import get_task_store

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/task/{task_id}/stream")
async def task_event_stream(websocket: WebSocket, task_id: str):
    """
    WebSocket 端点 — 实时推送任务事件

    先检查任务是否存在，然后持续推送事件直到连接断开
    """
    await websocket.accept()
    logger.info(f"WebSocket connected for task {task_id}")

    store = get_task_store()
    record = store.get_sync(task_id)

    if not record:
        await websocket.send_json({
            "type": "error",
            "data": {"message": f"Task not found: {task_id}"},
            "timestamp": "",
        })
        await websocket.close()
        return

    event_bus = get_event_bus()

    try:
        async for event in event_bus.subscribe(task_id):
            try:
                await websocket.send_json(event.model_dump())
            except Exception:
                logger.warning(f"Failed to send event to WebSocket for task {task_id}")
                break
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for task {task_id}")
    except Exception as e:
        logger.exception(f"WebSocket error for task {task_id}")
    finally:
        try:
            await websocket.close()
        except Exception:
            pass
