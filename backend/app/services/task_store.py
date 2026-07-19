"""
TaskStore — 任务状态内存存储

职责:
  1. 保存所有任务的状态
  2. 支持按 ID 查询
  3. 定期清理过期任务

设计: 内存字典 + 异步锁，简单但满足演示需求
生产环境可替换为 Redis/PostgreSQL
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)


class TaskRecord:
    """单条任务记录"""
    def __init__(self, task_id: str, request: str, provider: str):
        self.task_id = task_id
        self.request = request
        self.provider = provider
        self.status = "pending"
        self.plan_summary: Optional[str] = None
        self.steps: list = []
        self.files_created: list[str] = []
        self.files_modified: list[str] = []
        self.final_report: Optional[str] = None
        self.error_message: Optional[str] = None
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.updated_at = self.created_at
        self.is_running = False

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "status": self.status,
            "plan": {
                "task_summary": self.plan_summary or "",
                "steps": self.steps,
            } if self.plan_summary else None,
            "files_created": self.files_created,
            "files_modified": self.files_modified,
            "final_report": self.final_report,
            "error_message": self.error_message,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class TaskStore:
    """任务状态管理器（内存版）"""

    def __init__(self):
        self._tasks: dict[str, TaskRecord] = {}
        self._lock = asyncio.Lock()

    async def create(self, task_id: str, request: str, provider: str) -> TaskRecord:
        """创建任务"""
        async with self._lock:
            record = TaskRecord(task_id, request, provider)
            self._tasks[task_id] = record
            return record

    async def get(self, task_id: str) -> Optional[TaskRecord]:
        """获取任务"""
        return self._tasks.get(task_id)

    async def update(self, task_id: str, **kwargs) -> None:
        """更新任务字段"""
        async with self._lock:
            record = self._tasks.get(task_id)
            if record:
                for key, value in kwargs.items():
                    if hasattr(record, key):
                        setattr(record, key, value)
                record.updated_at = datetime.now(timezone.utc).isoformat()

    async def delete(self, task_id: str) -> bool:
        """删除任务"""
        async with self._lock:
            if task_id in self._tasks:
                del self._tasks[task_id]
                return True
            return False

    async def list_all(self) -> list[TaskRecord]:
        """列出所有任务"""
        return list(self._tasks.values())

    def get_sync(self, task_id: str) -> Optional[TaskRecord]:
        """同步获取（用于 WebSocket）"""
        return self._tasks.get(task_id)


# 全局单例
_task_store: TaskStore | None = None


def get_task_store() -> TaskStore:
    global _task_store
    if _task_store is None:
        _task_store = TaskStore()
    return _task_store
