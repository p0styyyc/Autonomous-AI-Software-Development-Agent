"""FileReadTool 单元测试"""

from pathlib import Path
from app.tools.file_read import FileReadTool


class TestFileReadTool:
    """FileReadTool 测试套件"""

    def test_read_existing_file(self, workspace, sample_py_file):
        """测试读取已存在文件"""
        tool = FileReadTool(workspace_path=workspace)
        result = tool._run(path="sample.py")

        assert "FILE" in result
        assert "def hello()" in result
        assert "return 'world'" in result

    def test_read_file_not_found(self, workspace):
        """测试读取不存在的文件"""
        tool = FileReadTool(workspace_path=workspace)
        result = tool._run(path="nonexistent.py")

        assert "ERROR" in result
        assert "not found" in result

    def test_read_with_line_range(self, workspace, sample_py_file):
        """测试按行范围读取"""
        tool = FileReadTool(workspace_path=workspace)
        result = tool._run(path="sample.py", start_line=1, end_line=2)

        assert "def hello()" in result
        assert "return 'world'" in result
        assert "print(hello())" not in result

    def test_language_detection(self, workspace):
        """测试自动语言检测"""
        Path(workspace, "styles.css").write_text("body { color: red; }")
        tool = FileReadTool(workspace_path=workspace)
        result = tool._run(path="styles.css")

        assert "css" in result

    def test_path_traversal_blocked(self, workspace):
        """测试路径遍历攻击被阻止"""
        tool = FileReadTool(workspace_path=workspace)
        result = tool._run(path="../../../etc/passwd")

        assert "SECURITY ERROR" in result
