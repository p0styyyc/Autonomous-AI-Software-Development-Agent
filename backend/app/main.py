"""
Mini Background Coding Agent — FastAPI 应用入口

启动方式:
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理：启动时初始化，关闭时清理资源"""
    settings = get_settings()
    logger.info(f"🚀 Mini Background Coding Agent 启动中...")
    logger.info(f"   LLM Provider: {settings.default_provider}")
    logger.info(f"   Default Model: {settings.default_model}")
    logger.info(f"   Workspace: {settings.workspace_path}")
    logger.info(f"   Sandbox Image: {settings.sandbox_image}")

    if not settings.is_llm_configured:
        logger.warning("⚠️  未配置任何 LLM API Key，Agent 将无法正常工作")
        logger.warning("   请复制 .env.example 为 .env 并填入 API Key")

    yield  # 应用运行中...

    logger.info("👋 Mini Background Coding Agent 关闭")


def create_app() -> FastAPI:
    """创建并配置 FastAPI 应用实例"""
    settings = get_settings()

    app = FastAPI(
        title="Mini Background Coding Agent",
        description="一个简化但完整的自主编程 Agent 系统，展示 AI 应用工程能力",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # CORS — 允许前端跨域访问
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 注册路由
    from app.api.router import api_router
    app.include_router(api_router, prefix="/api/v1")

    # 健康检查端点
    @app.get("/health", tags=["System"])
    async def health_check():
        return {
            "status": "healthy",
            "version": "1.0.0",
            "llm_configured": settings.is_llm_configured,
        }

    return app


# 应用实例（uvicorn 入口点）
app = create_app()
