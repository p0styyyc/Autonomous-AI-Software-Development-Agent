"""Review Agent 单元测试"""

import json
from unittest.mock import MagicMock

import pytest
from langchain_core.messages import AIMessage

from app.agents.reviewer import ReviewAgent


VALID_REVIEW_JSON = json.dumps({
    "passed": True,
    "overall_score": 88,
    "dimensions": {
        "functionality": {"score": 95, "comment": "Works correctly"},
        "code_quality": {"score": 90, "comment": "Well structured"},
        "security": {"score": 85, "comment": "No issues found"},
        "performance": {"score": 85, "comment": "Efficient"},
        "readability": {"score": 85, "comment": "Clean code"},
    },
    "critical_issues": [],
    "suggestions": ["Add more tests", "Improve error messages"],
    "summary": "Great work overall",
})

FAILED_REVIEW_JSON = json.dumps({
    "passed": False,
    "overall_score": 45,
    "dimensions": {
        "functionality": {"score": 30, "comment": "Does not work"},
        "code_quality": {"score": 50, "comment": "No type hints"},
        "security": {"score": 40, "comment": "Hardcoded API key"},
        "performance": {"score": 60, "comment": "Acceptable"},
        "readability": {"score": 45, "comment": "Poor naming"},
    },
    "critical_issues": ["Hardcoded secret: OPENAI_API_KEY on line 5"],
    "suggestions": ["Use environment variables", "Add type hints"],
    "summary": "Needs significant revision",
})


@pytest.fixture
def mock_llm():
    llm = MagicMock()
    llm.invoke.return_value = AIMessage(content=VALID_REVIEW_JSON)
    return llm


@pytest.fixture
def reviewer(mock_llm):
    return ReviewAgent(llm=mock_llm)


class TestReviewAgent:
    def test_review_passed(self, reviewer):
        """测试通过审查"""
        result = reviewer.review(
            step_description="Create main.py",
            expected_output="App starts",
            code="print('hello')",
            execution_result="[SUCCESS] executed",
        )
        assert result["passed"] is True
        assert result["overall_score"] >= 70
        assert len(result["suggestions"]) >= 0

    def test_review_failed(self, reviewer):
        """测试未通过审查"""
        reviewer.llm.invoke.return_value = AIMessage(content=FAILED_REVIEW_JSON)

        result = reviewer.review(
            step_description="Secure login endpoint",
            expected_output="Authentication works",
            code="API_KEY = 'sk-abc123'\ndef login(): pass",
            execution_result="[ERROR] crashed",
        )
        assert result["passed"] is False
        assert result["overall_score"] < 70
        assert len(result["critical_issues"]) > 0

    def test_review_without_execution(self, reviewer):
        """测试无执行结果的审查"""
        result = reviewer.review(
            step_description="Add config",
            expected_output="Config loaded",
            code="from os import environ\nAPI_KEY = environ.get('KEY')",
            execution_result="",
        )
        assert "passed" in result

    def test_review_bad_json_fallback(self, reviewer):
        """测试 LLM 返回无效 JSON 时的降级处理"""
        reviewer.llm.invoke.return_value = AIMessage(content="not valid json at all")

        result = reviewer.review(
            step_description="test",
            expected_output="test",
            code="# nothing",
        )
        assert result["passed"] is False
        assert len(result["critical_issues"]) > 0
        assert "valid JSON" in result["critical_issues"][0]

    def test_review_prompt_includes_code(self, reviewer):
        """测试审查 prompt 包含代码内容"""
        reviewer.llm.invoke.return_value = AIMessage(content=VALID_REVIEW_JSON)
        reviewer.review(
            step_description="Create app",
            expected_output="App runs",
            code="def main():\n    print('hello')",
        )
        call_args = reviewer.llm.invoke.call_args
        messages = call_args[0][0]
        prompt_text = str(messages)
        assert "def main()" in prompt_text
        assert "print('hello')" in prompt_text

    def test_name_is_reviewer(self, reviewer):
        assert reviewer.name == "reviewer"
