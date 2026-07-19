"""EventBus 单元测试"""

import asyncio
import pytest
from app.models.ws_event import WSEvent
from app.services.event_bus import EventBus, get_event_bus


class TestEventBus:
    def test_publish_and_get_history(self):
        bus = EventBus()
        event = WSEvent.create("task_started", task_id="abc")
        bus.publish(event)

        history = bus.get_history("abc")
        assert len(history) == 1
        assert history[0].type == "task_started"

    def test_callback_invoked(self):
        bus = EventBus()
        received = []

        def callback(event):
            received.append(event.type)

        bus.on_event("task1", callback)
        bus.publish(WSEvent.create("planning_started", task_id="task1"))
        bus.publish(WSEvent.create("planning_completed", task_id="task1"))

        assert len(received) == 2
        assert "planning_started" in received

    def test_multiple_subscribers(self):
        bus = EventBus()
        results1 = []
        results2 = []

        bus.on_event("task1", lambda e: results1.append(e.type))
        bus.on_event("task1", lambda e: results2.append(e.type))

        bus.publish(WSEvent.create("coding_started", task_id="task1"))
        assert len(results1) == 1
        assert len(results2) == 1

    def test_different_tasks_isolated(self):
        bus = EventBus()
        results_a = []
        results_b = []

        bus.on_event("task_a", lambda e: results_a.append(e.type))
        bus.on_event("task_b", lambda e: results_b.append(e.type))

        bus.publish(WSEvent.create("step_started", task_id="task_a"))
        assert len(results_a) == 1
        assert len(results_b) == 0

    def test_history_limit(self):
        bus = EventBus()
        bus._max_history = 5
        for i in range(10):
            bus.publish(WSEvent.create("log", task_id="t", message=str(i)))

        history = bus.get_history("t")
        assert len(history) == 5
        # 应该保留最新的 5 条
        assert history[0].data["message"] == "5"

    def test_clear_removes_all(self):
        bus = EventBus()
        bus.publish(WSEvent.create("task_started", task_id="t"))
        bus.clear("t")
        assert bus.get_history("t") == []

    @pytest.mark.asyncio
    async def test_subscribe_async_generator(self):
        bus = EventBus()

        # 先发布一些历史事件
        bus.publish(WSEvent.create("log", task_id="t", message="history1"))

        events = []
        async def collect():
            async for event in bus.subscribe("t"):
                events.append(event.type)
                if len(events) >= 2:
                    break

        # 同时发布新事件
        async def publish_later():
            await asyncio.sleep(0.05)
            bus.publish(WSEvent.create("coding_started", task_id="t"))

        await asyncio.gather(collect(), publish_later())

        assert "log" in events  # 历史
        assert "coding_started" in events  # 新事件


class TestGlobalEventBus:
    def test_singleton(self):
        bus1 = get_event_bus()
        bus2 = get_event_bus()
        assert bus1 is bus2
