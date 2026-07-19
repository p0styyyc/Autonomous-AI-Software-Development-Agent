"""Execution Agent 单元测试"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from langchain_core.messages import AIMessage

from app.agents.executor import ExecutionAgent, collect_workspace_files


@pytest.fixture
def mock_llm():
    llm = MagicMock()
    llm.invoke.return_value = AIMessage(content="Execution analysis complete")
    return llm


@pytest.fixture
def executor(mock_llm, workspace):
    return ExecutionAgent(llm=mock_llm, workspace_path=workspace)


class TestExecutionAgent:
    def test_execute_with_valid_files(self, executor):
        """测试使用有效文件执行"""
        result = executor.execute(
            code_files={"main.py": "print('hello')"},
            entry_point="main.py",
        )
        assert result is not None
        # 没有 Docker 时应返回 dry-run
        assert result.success or "DRY RUN" in result.stdout

    def test_execute_missing_entry_point(self, executor):
        """测试入口文件不存在"""
        result = executor.execute(
            code_files={"other.py": "print('hi')"},
            entry_point="main.py",
        )
        assert result.success is False
        assert "not found" in result.stderr

    def test_execute_with_multiple_files(self, executor):
        """测试多文件项目执行"""
        result = executor.execute(
            code_files={
                "main.py": "from utils import greet\ngreet()",
                "utils.py": "def greet():\n    print('Hello from utils')",
            },
            entry_point="main.py",
        )
        assert result is not None

    def test_execute_and_analyze_calls_llm(self, executor):
        """测试 execute_and_analyze 调用 LLM 分析"""
        result = executor.execute_and_analyze(
            code_files={"main.py": "print('test')"},
            step_description="Print test message",
            expected_output="test",
            entry_point="main.py",
        )
        assert len(result) > 0
        executor.llm.invoke.assert_called()


class TestCollectWorkspaceFiles:
    def test_empty_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            files = collect_workspace_files(tmp)
            assert files == {}

    def test_collects_files_recursively(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "main.py").write_text("print(1)")
            (root / "sub").mkdir()
            (root / "sub" / "utils.py").write_text("x = 1")

            files = collect_workspace_files(tmp)

            assert "main.py" in files
            assert "sub/utils.py" in files
            assert files["main.py"] == "print(1)"
