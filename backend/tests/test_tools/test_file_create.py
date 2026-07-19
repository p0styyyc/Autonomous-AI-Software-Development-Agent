"""FileCreateTool 单元测试"""

from pathlib import Path
from app.tools.file_create import FileCreateTool


class TestFileCreateTool:
    """FileCreateTool 测试套件"""

    def test_create_new_file(self, workspace):
        """测试创建新文件"""
        tool = FileCreateTool(workspace_path=workspace)
        result = tool._run(path="test.py", content="print(1)")

        assert "SUCCESS" in result
        assert Path(workspace, "test.py").exists()
        assert Path(workspace, "test.py").read_text() == "print(1)"

    def test_create_nested_file(self, workspace):
        """测试创建嵌套目录中的文件（自动创建父目录）"""
        tool = FileCreateTool(workspace_path=workspace)
        result = tool._run(path="deep/nested/file.py", content="x = 1")

        assert "SUCCESS" in result
        assert Path(workspace, "deep/nested/file.py").exists()

    def test_overwrite_existing_file(self, workspace):
        """测试覆盖已存在文件"""
        tool = FileCreateTool(workspace_path=workspace)
        tool._run(path="config.json", content='{"v": 1}')
        result = tool._run(path="config.json", content='{"v": 2}')

        assert "SUCCESS" in result
        assert "overwritten" in result
        assert Path(workspace, "config.json").read_text() == '{"v": 2}'

    def test_path_traversal_blocked(self, workspace):
        """测试路径遍历攻击被阻止"""
        tool = FileCreateTool(workspace_path=workspace)
        result = tool._run(path="../../../etc/hacked", content="malicious")

        assert "SECURITY ERROR" in result
        assert not Path(workspace, "../../../etc/hacked").exists()

    def test_path_traversal_with_dotdots(self, workspace):
        """测试使用 .. 的路径遍历"""
        tool = FileCreateTool(workspace_path=workspace)
        result = tool._run(path="subdir/../../escape.py", content="bad")

        assert "SECURITY ERROR" in result
