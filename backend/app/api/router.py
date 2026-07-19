"""API 路由注册"""

from fastapi import APIRouter

from app.api.task import router as task_router
from app.api.ws import router as ws_router

api_router = APIRouter()
api_router.include_router(task_router, tags=["Task"])
api_router.include_router(ws_router, tags=["WebSocket"])
