"""Planner Agent 单元测试 — Mock LLM 避免真实 API 调用"""

import json
from unittest.mock import MagicMock

import pytest
from langchain_core.messages import AIMessage

from app.agents.planner import PlannerAgent, _extract_json
from app.core.llm import create_llm, LLMProvider


# ── 测试数据 ──────────────────────────────────

VALID_PLAN_JSON = json.dumps({
    "task_summary": "Create a Flask weather API with health check endpoint",
    "tech_stack": {"language": "python", "framework": "flask"},
    "steps": [
        {
            "id": 1,
            "description": "Create project skeleton",
            "files_to_create": ["main.py", "requirements.txt"],
            "files_to_modify": [],
            "expected_output": "App starts without error",
            "complexity": 2,
            "depends_on": [],
        },
        {
            "id": 2,
            "description": "Add weather endpoint",
            "files_to_create": ["weather.py"],
            "files_to_modify": ["main.py"],
            "expected_output": "/weather?city=beijing returns JSON",
            "complexity": 3,
            "depends_on": [1],
        },
    ],
    "estimated_total_time": "2-3 minutes",
})


# ── Fixtures ──────────────────────────────────

@pytest.fixture
def mock_llm():
    """创建 Mock LLM，返回预设的 plan JSON"""
    llm = MagicMock()
    response = AIMessage(content=VALID_PLAN_JSON)
    llm.invoke.return_value = response
    return llm


@pytest.fixture
def planner(mock_llm):
    """创建 Planner Agent 实例"""
    return PlannerAgent(llm=mock_llm)


# ── Tests ─────────────────────────────────────

class TestPlannerAgent:
    """Planner Agent 测试套件"""

    def test_plan_returns_valid_structure(self, planner):
        """测试 plan 方法返回结构化的计划"""
        plan = planner.plan("Create a weather API")

        assert "task_summary" in plan
        assert "steps" in plan
        assert len(plan["steps"]) == 2
        assert plan["steps"][0]["id"] == 1
        assert plan["steps"][1]["depends_on"] == [1]

    def test_plan_step_has_required_defaults(self, planner):
        """测试步骤缺失字段时补全默认值"""
        # 使用缺少部分字段的 JSON
        incomplete = json.dumps({
            "task_summary": "test",
            "steps": [{"id": 1, "description": "do something"}],
        })
        planner.llm.invoke.return_value = AIMessage(content=incomplete)

        plan = planner.plan("test request")
        step = plan["steps"][0]

        assert step["files_to_create"] == []  # 默认值
        assert step["files_to_modify"] == []  # 默认值
        assert step["complexity"] == 3  # 默认值

    def test_plan_missing_steps_field_raises(self, planner):
        """测试缺少 steps 字段时抛出异常"""
        bad_json = json.dumps({"task_summary": "test"})
        planner.llm.invoke.return_value = AIMessage(content=bad_json)

        with pytest.raises(ValueError):
            planner.plan("test")

    def test_plan_empty_steps_raises(self, planner):
        """测试 steps 为空列表时抛出异常"""
        bad_json = json.dumps({"task_summary": "test", "steps": []})
        planner.llm.invoke.return_value = AIMessage(content=bad_json)

        with pytest.raises(ValueError):
            planner.plan("test")

    def test_plan_with_markdown_code_block(self, planner):
        """测试 LLM 返回 markdown 代码块时能正确提取"""
        md_wrapped = f"Here is the plan:\n```json\n{VALID_PLAN_JSON}\n```\nHope this works!"
        planner.llm.invoke.return_value = AIMessage(content=md_wrapped)

        plan = planner.plan("test")
        assert len(plan["steps"]) == 2

    def test_plan_with_explanatory_text(self, planner):
        """测试 LLM 在 JSON 前后加说明文字"""
        wrapped = f"Sure! Here is your plan:\n{VALID_PLAN_JSON}\nLet me know if you need changes."
        planner.llm.invoke.return_value = AIMessage(content=wrapped)

        plan = planner.plan("test")
        assert plan["task_summary"] == "Create a Flask weather API with health check endpoint"


class TestExtractJson:
    """JSON 提取函数测试"""

    def test_pure_json(self):
        assert "key" in _extract_json('{"key": "value"}')

    def test_markdown_code_block(self):
        result = _extract_json('```json\n{"a": 1}\n```')
        assert "a" in result

    def test_with_surrounding_text(self):
        result = _extract_json('hello {"b": 2} world')
        assert "b" in result

    def test_multiple_objects_takes_first_to_last(self):
        result = _extract_json('{"first": 1} middle {"second": 2}')
        assert "first" in result
        assert "second" in result
