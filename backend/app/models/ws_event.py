"""
WebSocket 事件模型 — 实时推送 Agent 执行状态给前端

事件类型设计原则:
  - 每个 Agent 阶段都有 start/success/fail 事件三元组
  - 事件类型用过去式（已发生），便于前端根据 type 做 UI 更新
  - data 字段灵活，不同事件携带不同 payload
"""

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field


# 所有可能的 WebSocket 事件类型
WSEventType = Literal[
    # 任务生命周期
    "task_started",
    "task_completed",
    "task_failed",
    # 规划阶段
    "planning_started",
    "planning_completed",
    # 步骤执行
    "step_started",
    "step_completed",
    # 编码阶段
    "coding_started",
    "code_generated",
    "coding_completed",
    # 执行阶段
    "executing_started",
    "execution_success",
    "execution_error",
    # 审查阶段
    "reviewing_started",
    "review_pass",
    "review_fail",
    # 重试
    "retry_started",
    # 通用
    "log",
    "error",
]


class WSEvent(BaseModel):
    """
    WebSocket 事件 — 通过 WS 连接推送给前端

    示例:
        {
            "type": "code_generated",
            "data": {
                "file": "main.py",
                "content": "from flask import Flask\n...",
                "step_id": 2
            },
            "timestamp": "2026-07-19T10:00:05Z"
        }
    """
    type: WSEventType = Field(..., description="事件类型")
    data: dict[str, Any] = Field(
        default_factory=dict,
        description="事件携带的数据，结构因 type 而异",
    )
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="事件发生时间 (ISO 8601 UTC)",
    )

    @classmethod
    def create(cls, event_type: WSEventType, **data: Any) -> "WSEvent":
        """快捷工厂方法"""
        return cls(type=event_type, data=data)
