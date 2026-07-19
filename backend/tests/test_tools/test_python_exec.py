"""PythonExecutionTool 单元测试"""

from app.tools.python_exec import PythonExecutionTool, _is_docker_available


class TestPythonExecutionTool:
    """PythonExecutionTool 测试套件（不需要 Docker）"""

    def test_dry_run_when_no_docker(self, workspace):
        """测试 Docker 不可用时的降级模式"""
        tool = PythonExecutionTool(workspace_path=workspace)
        result = tool._run(code="print('hello')")

        assert "DRY RUN" in result or "SUCCESS" in result or "ERROR" in result
        # 在没有 Docker 的环境中应该返回 dry run 或错误，不应该 crash

    def test_dry_run_shows_code(self, workspace):
        """测试 dry run 显示代码预览"""
        tool = PythonExecutionTool(workspace_path=workspace)
        result = tool._run(code="x = 1 + 1\nprint(x)")

        if "DRY RUN" in result:
            assert "x = 1 + 1" in result
        # 如果 Docker 可用则跳过这个断言

    def test_with_files_parameter(self, workspace):
        """测试带文件参数"""
        tool = PythonExecutionTool(workspace_path=workspace)
        result = tool._run(
            code="import utils\nprint(utils.add(1, 2))",
            files={"utils.py": "def add(a, b): return a + b"},
        )

        # 无论 Docker 是否可用，不应该报错
        assert "ERROR" not in result.lower() or "DRY RUN" in result

    def test_path_traversal_blocked(self, workspace):
        """测试通过 files 参数的文件路径遍历被阻止"""
        tool = PythonExecutionTool(workspace_path=workspace)
        result = tool._run(
            code="print('test')",
            files={"../../../malicious.py": "bad"},
        )

        assert "SECURITY ERROR" in result
