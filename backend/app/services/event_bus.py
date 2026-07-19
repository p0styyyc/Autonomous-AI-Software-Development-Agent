"""
EventBus — 发布/订阅事件总线

职责:
  1. Agent 执行过程中发布事件
  2. WebSocket 订阅事件并推送给前端
  3. 支持内存模式（开发）和 Redis 模式（生产）

设计模式: Observer Pattern
"""

import asyncio
import logging
from collections import defaultdict
from typing import Any, AsyncIterator, Callable

from app.models.ws_event import WSEvent

logger = logging.getLogger(__name__)

# 回调函数类型: async (event) -> None
Subscriber = Callable[[WSEvent], Any]


class EventBus:
    """
    事件总线

    使用示例:
        bus = EventBus()

        # 发布者
        bus.publish(WSEvent.create("task_started", task_id="abc"))

        # 订阅者
        async for event in bus.subscribe("abc"):
            print(event.type)

        # 或回调模式
        bus.on_event("abc", lambda e: print(e.type))
    """

    def __init__(self):
        # task_id → [asyncio.Queue]（每个 WebSocket 连接一个 Queue）
        self._queues: dict[str, list[asyncio.Queue]] = defaultdict(list)
        # task_id → [callback]
        self._callbacks: dict[str, list[Subscriber]] = defaultdict(list)
        # 存储最近的事件（用于新订阅者补发历史）
        self._history: dict[str, list[WSEvent]] = defaultdict(list)
        self._max_history = 50  # 每个任务最多保留 50 条历史

    def publish(self, event: WSEvent) -> None:
        """
        发布事件到所有订阅者

        Args:
            event: WebSocket 事件
        """
        task_id = event.data.get("task_id", "")

        # 存入历史
        self._history[task_id].append(event)
        if len(self._history[task_id]) > self._max_history:
            self._history[task_id] = self._history[task_id][-self._max_history:]

        # 推送到所有 Queue
        for queue in self._queues.get(task_id, []):
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                logger.warning(f"Event queue full for task {task_id}, dropping event")

        # 通知所有回调
        for callback in self._callbacks.get(task_id, []):
            try:
                result = callback(event)
                # 如果回调是异步的，忽略（回调模式不支持 async）
                if asyncio.iscoroutine(result):
                    pass
            except Exception:
                logger.exception(f"Event callback failed for task {task_id}")

    async def subscribe(self, task_id: str) -> AsyncIterator[WSEvent]:
        """
        订阅任务事件（生成器模式，用于 WebSocket）

        先补发历史事件，然后持续 yield 新事件。
        当 WebSocket 断开时，generator 自动清理。

        使用示例:
            async for event in bus.subscribe("abc"):
                await ws.send_json(event.model_dump())
        """
        queue: asyncio.Queue = asyncio.Queue(maxsize=200)

        # 注册队列
        self._queues[task_id].append(queue)

        try:
            # 先发送历史事件
            for event in self._history.get(task_id, []):
                yield event

            # 持续监听新事件
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield event
                except asyncio.TimeoutError:
                    # 发送心跳防止连接断开
                    yield WSEvent.create(
                        "log",
                        task_id=task_id,
                        message="heartbeat",
                    )
        finally:
            # 清理：WebSocket 断开时移除队列
            if queue in self._queues.get(task_id, []):
                self._queues[task_id].remove(queue)
            # 清理空列表
            if task_id in self._queues and not self._queues[task_id]:
                del self._queues[task_id]
            logger.debug(f"Subscriber disconnected for task {task_id}")

    def on_event(self, task_id: str, callback: Subscriber) -> None:
        """注册回调函数（非 WebSocket 场景）"""
        self._callbacks[task_id].append(callback)

    def get_history(self, task_id: str) -> list[WSEvent]:
        """获取任务历史事件"""
        return list(self._history.get(task_id, []))

    def clear(self, task_id: str) -> None:
        """清理任务相关的所有订阅和历史"""
        self._queues.pop(task_id, None)
        self._callbacks.pop(task_id, None)
        self._history.pop(task_id, None)


# 全局事件总线单例
_event_bus: EventBus | None = None


def get_event_bus() -> EventBus:
    """获取全局 EventBus 单例"""
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
    return _event_bus
