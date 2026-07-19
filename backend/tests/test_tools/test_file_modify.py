"""FileModifyTool 单元测试"""

from pathlib import Path
from app.tools.file_modify import FileModifyTool


class TestFileModifyTool:
    """FileModifyTool 测试套件"""

    @staticmethod
    def _setup_file(workspace) -> Path:
        """创建测试文件"""
        p = Path(workspace) / "code.py"
        p.write_text("def foo():\n    return 'old'\n\n# end\n")
        return p

    def test_replace_content(self, workspace):
        """测试替换内容"""
        self._setup_file(workspace)
        tool = FileModifyTool(workspace_path=workspace)
        result = tool._run(
            path="code.py",
            operation="replace",
            old_content="return 'old'",
            new_content="return 'new'",
        )

        assert "SUCCESS" in result
        content = Path(workspace, "code.py").read_text()
        assert "return 'new'" in content
        assert "return 'old'" not in content

    def test_insert_at_line(self, workspace):
        """测试在指定行插入"""
        self._setup_file(workspace)
        tool = FileModifyTool(workspace_path=workspace)
        result = tool._run(
            path="code.py",
            operation="insert",
            new_content="# inserted comment",
            line_number=2,
        )

        assert "SUCCESS" in result
        lines = Path(workspace, "code.py").read_text().split("\n")
        assert lines[2] == "# inserted comment"

    def test_append_to_end(self, workspace):
        """测试追加到文件末尾"""
        self._setup_file(workspace)
        tool = FileModifyTool(workspace_path=workspace)
        result = tool._run(
            path="code.py",
            operation="append",
            new_content="# appended",
        )

        assert "SUCCESS" in result
        content = Path(workspace, "code.py").read_text()
        assert content.endswith("# appended\n")

    def test_delete_lines(self, workspace):
        """测试删除指定行"""
        self._setup_file(workspace)
        tool = FileModifyTool(workspace_path=workspace)
        result = tool._run(
            path="code.py",
            operation="delete_lines",
            line_number=4,
            count=1,
        )

        assert "SUCCESS" in result
        content = Path(workspace, "code.py").read_text()
        assert "# end" not in content

    def test_replace_not_found(self, workspace):
        """测试替换不存在的内容"""
        self._setup_file(workspace)
        tool = FileModifyTool(workspace_path=workspace)
        result = tool._run(
            path="code.py",
            operation="replace",
            old_content="this does not exist",
            new_content="nothing",
        )

        assert "ERROR" in result
        assert "not found" in result

    def test_modify_nonexistent_file(self, workspace):
        """测试修改不存在的文件"""
        tool = FileModifyTool(workspace_path=workspace)
        result = tool._run(
            path="nope.py",
            operation="append",
            new_content="x",
        )

        assert "ERROR" in result
        assert "not found" in result

    def test_path_traversal_blocked(self, workspace):
        """测试路径遍历攻击被阻止"""
        tool = FileModifyTool(workspace_path=workspace)
        result = tool._run(
            path="../../../etc/hosts",
            operation="append",
            new_content="evil",
        )

        assert "SECURITY ERROR" in result
