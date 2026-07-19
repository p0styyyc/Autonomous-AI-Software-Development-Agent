"""
Task 相关数据模型 — 任务创建、计划、步骤的结构化定义
"""

from datetime import datetime
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, Field


# ── 请求模型 ──────────────────────────────────

class TaskCreateRequest(BaseModel):
    """创建任务请求"""
    request: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="用户的自然语言编程需求",
        examples=["帮我创建一个Python天气查询API，包含 /health 和 /weather?city=beijing"],
    )
    provider: str = Field(
        default="openai",
        pattern="^(openai|deepseek)$",
        description="LLM Provider",
    )
    model: Optional[str] = Field(
        default=None,
        description="模型名称，不指定则使用 provider 默认模型",
    )


# ── 响应模型 ──────────────────────────────────

class TaskCreateResponse(BaseModel):
    """创建任务响应"""
    task_id: str
    status: str = "pending"
    created_at: str


class StepInfo(BaseModel):
    """单个步骤信息"""
    id: int
    description: str
    files_to_create: list[str] = Field(default_factory=list)
    files_to_modify: list[str] = Field(default_factory=list)
    expected_output: str = ""
    complexity: int = Field(default=1, ge=1, le=5)
    depends_on: list[int] = Field(default_factory=list)
    status: str = "pending"  # pending | in_progress | done | failed


class PlanInfo(BaseModel):
    """计划信息"""
    task_summary: str
    tech_stack: dict[str, str] = Field(default_factory=dict)
    steps: list[StepInfo] = Field(default_factory=list)
    estimated_total_time: str = ""


class TaskStatus(BaseModel):
    """任务状态查询响应"""
    task_id: str
    status: str
    plan: Optional[PlanInfo] = None
    files_created: list[str] = Field(default_factory=list)
    files_modified: list[str] = Field(default_factory=list)
    final_report: Optional[str] = None
    error_message: Optional[str] = None
    created_at: str
    updated_at: str


class FileInfo(BaseModel):
    """文件信息"""
    path: str
    content: str
    size_bytes: int
    language: str = ""


# ── 工具函数 ──────────────────────────────────

def generate_task_id() -> str:
    """生成短任务 ID（便于展示和日志查找）"""
    return uuid4().hex[:12]
