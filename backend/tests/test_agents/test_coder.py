"""Coding Agent 单元测试"""

from unittest.mock import MagicMock

import pytest
from langchain_core.messages import AIMessage

from app.agents.coder import CodingAgent


@pytest.fixture
def mock_llm():
    llm = MagicMock()
    llm.invoke.return_value = AIMessage(content="Code generated successfully")
    llm.bind_tools.return_value = llm
    return llm


@pytest.fixture
def coder(mock_llm):
    return CodingAgent(llm=mock_llm)


class TestCodingAgent:
    def test_implement_step_without_tools(self, coder):
        """测试无 Tool 模式下的代码生成"""
        step = {
            "id": 1,
            "description": "Create main.py",
            "files_to_create": ["main.py"],
            "files_to_modify": [],
            "expected_output": "App starts",
        }
        result = coder.implement_step(
            task_summary="Create a weather API",
            step=step,
            workspace_state="(empty)",
        )
        assert len(result) > 0

    def test_implement_step_prompt_contains_step_info(self, coder):
        """测试 prompt 包含步骤信息"""
        step = {
            "id": 2,
            "description": "Add tests",
            "files_to_create": ["test_app.py"],
            "files_to_modify": [],
            "expected_output": "All tests pass",
        }

        # 捕获传给 LLM 的消息
        coder.llm.invoke.return_value = AIMessage(content="done")
        coder.implement_step("Build API", step, "(empty)")

        call_args = coder.llm.invoke.call_args
        messages = call_args[0][0]
        prompt_text = str(messages)

        assert "Build API" in prompt_text
        assert "Add tests" in prompt_text
        assert "test_app.py" in prompt_text

    def test_name_is_coder(self, coder):
        assert coder.name == "coder"

    def test_system_prompt_is_not_empty(self, coder):
        assert len(coder.system_prompt) > 100
        assert "Senior Software Engineer" in coder.system_prompt
