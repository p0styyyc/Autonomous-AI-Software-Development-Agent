"""Orchestrator 单元测试 — Mock Agent 避免真实 LLM 调用"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import AIMessage

from app.core.orchestrator import AgentOrchestrator
from app.core.state import create_initial_state


# ── 测试数据 ──────────────────────────────────

VALID_PLAN = {
    "task_summary": "Create a simple hello world Python script",
    "tech_stack": {"language": "python"},
    "steps": [
        {
            "id": 1,
            "description": "Create main.py with hello world",
            "files_to_create": ["main.py"],
            "files_to_modify": [],
            "expected_output": "Script prints hello world",
            "complexity": 1,
            "depends_on": [],
        }
    ],
    "estimated_total_time": "1 minute",
}

PASS_REVIEW = {
    "passed": True,
    "overall_score": 90,
    "dimensions": {},
    "critical_issues": [],
    "suggestions": [],
    "summary": "Looks good",
}


class TestAgentOrchestrator:
    """Orchestrator 测试套件（Mock 所有 LLM 调用）"""

    @pytest.fixture
    def mock_llm(self):
        """创建 Mock LLM"""
        llm = MagicMock()
        llm.invoke.return_value = AIMessage(content=json.dumps(VALID_PLAN))
        llm.bind_tools.return_value = llm
        return llm

    @pytest.fixture
    def orchestrator(self, workspace):
        """创建 Orchestrator 实例"""
        from app.services.workspace import WorkspaceManager
        from app.services.event_bus import EventBus

        wm = WorkspaceManager(base_dir=workspace)
        bus = EventBus()
        return AgentOrchestrator(workspace=wm, event_bus=bus)

    def test_graph_is_built(self, orchestrator):
        """测试 LangGraph 图可以成功构建"""
        assert orchestrator._graph is not None

    def test_initial_state_creation(self):
        """测试初始状态创建"""
        state = create_initial_state("test-1", "Create hello world")
        assert state["task_id"] == "test-1"
        assert state["status"] == "pending"
        assert state["retry_count"] == 0

    @pytest.mark.asyncio
    @patch("app.core.orchestrator.create_planner_llm")
    @patch("app.core.orchestrator.create_coder_llm")
    @patch("app.core.orchestrator.create_reviewer_llm")
    @patch("app.core.orchestrator.create_llm")
    async def test_run_single_step_task(
        self, mock_create_llm, mock_reviewer_llm, mock_coder_llm, mock_planner_llm, orchestrator
    ):
        """测试完整的单步骤任务执行流程"""
        # Mock Planner
        planner_llm = MagicMock()
        planner_llm.invoke.return_value = AIMessage(content=json.dumps(VALID_PLAN))
        mock_planner_llm.return_value = planner_llm

        # Mock Coder
        coder_llm = MagicMock()
        coder_llm.bind_tools.return_value = coder_llm
        coder_llm.invoke.return_value = AIMessage(content="I've created main.py")
        mock_coder_llm.return_value = coder_llm

        # Mock Executor LLM
        exec_llm = MagicMock()
        exec_llm.invoke.return_value = AIMessage(content="Execution ok")
        mock_create_llm.return_value = exec_llm

        # Mock Reviewer
        reviewer_llm = MagicMock()
        reviewer_llm.invoke.return_value = AIMessage(content=json.dumps(PASS_REVIEW))
        mock_reviewer_llm.return_value = reviewer_llm

        # Run orchestrator
        result = await orchestrator.run(
            task_id="test-single-step",
            user_request="Create hello world script",
        )

        assert result is not None

    def test_route_after_review_pass_then_finalize(self, orchestrator):
        """测试审查通过后路由到 finalize（单步骤任务）"""
        state = create_initial_state("t1", "test")
        state["steps"] = [{"id": 1, "description": "Only step"}]
        state["current_step_index"] = 0
        state["review_result"] = {"passed": True, "overall_score": 90}
        state["retry_count"] = 0
        state["max_retries"] = 3

        route = orchestrator._route_after_review(state)
        assert route == "finalize"

    def test_route_after_review_fail_then_retry(self, orchestrator):
        """测试审查失败后路由到 retry"""
        state = create_initial_state("t1", "test")
        state["steps"] = [{"id": 1, "description": "Step 1"}]
        state["current_step_index"] = 0
        state["review_result"] = {"passed": False, "overall_score": 40}
        state["retry_count"] = 0
        state["max_retries"] = 3

        route = orchestrator._route_after_review(state)
        assert route == "retry"

    def test_route_after_review_max_retries_exceeded(self, orchestrator):
        """测试超过最大重试次数后跳过当前步骤"""
        state = create_initial_state("t1", "test")
        state["steps"] = [
            {"id": 1, "description": "Step 1"},
            {"id": 2, "description": "Step 2"},
        ]
        state["current_step_index"] = 0
        state["review_result"] = {"passed": False, "overall_score": 30}
        state["retry_count"] = 3  # 已达到最大
        state["max_retries"] = 3

        route = orchestrator._route_after_review(state)
        assert route == "next_step"

    def test_route_multi_step_continue(self, orchestrator):
        """测试多步骤任务通过后继续下一步"""
        state = create_initial_state("t1", "test")
        state["steps"] = [
            {"id": 1, "description": "Step 1"},
            {"id": 2, "description": "Step 2"},
        ]
        state["current_step_index"] = 0
        state["review_result"] = {"passed": True, "overall_score": 90}
        state["retry_count"] = 0
        state["max_retries"] = 3

        route = orchestrator._route_after_review(state)
        assert route == "next_step"

    def test_report_generation(self, orchestrator):
        """测试最终报告生成"""
        state = create_initial_state("t1", "test")
        state["plan_summary"] = "Created weather API"
        state["steps"] = [
            {"id": 1, "description": "Create skeleton"},
            {"id": 2, "description": "Add endpoints"},
        ]
        state["current_step_index"] = 2
        state["files_created"] = ["main.py", "api.py"]
        state["files_modified"] = []
        state["review_result"] = {
            "passed": True,
            "overall_score": 88,
            "summary": "Great work",
            "suggestions": ["Add more tests"],
        }

        report = orchestrator._generate_report(state)

        assert "Development Report" in report
        assert "weather API" in report
        assert "main.py" in report
        assert "Great work" in report
        assert "Add more tests" in report
