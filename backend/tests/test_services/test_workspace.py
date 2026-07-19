"""WorkspaceManager 单元测试"""

import pytest
from pathlib import Path
from app.services.workspace import WorkspaceManager


class TestWorkspaceManager:
    def test_create_workspace(self, workspace):
        wm = WorkspaceManager(base_dir=workspace)
        ws = wm.create("task1")
        assert ws.exists()
        assert ws.is_dir()

    def test_write_and_read_file(self, workspace):
        wm = WorkspaceManager(base_dir=workspace)
        wm.create("task1")
        wm.write_file("task1", "main.py", "print('hello')")
        content = wm.read_file("task1", "main.py")
        assert content == "print('hello')"

    def test_list_files(self, workspace):
        wm = WorkspaceManager(base_dir=workspace)
        wm.create("task1")
        wm.write_file("task1", "a.py", "1")
        wm.write_file("task1", "sub/b.py", "2")

        files = wm.list_files("task1")
        assert "a.py" in files
        assert "sub/b.py" in files
        assert len(files) == 2

    def test_get_file_tree(self, workspace):
        wm = WorkspaceManager(base_dir=workspace)
        wm.create("task1")
        wm.write_file("task1", "main.py", "code")

        tree = wm.get_file_tree("task1")
        assert "main.py" in tree

    def test_empty_workspace_summary(self, workspace):
        wm = WorkspaceManager(base_dir=workspace)
        wm.create("task1")
        summary = wm.get_workspace_summary("task1")
        assert "empty" in summary

    def test_path_traversal_blocked(self, workspace):
        wm = WorkspaceManager(base_dir=workspace)
        wm.create("task1")
        with pytest.raises(ValueError, match="Path traversal"):
            wm.write_file("task1", "../../../etc/passwd", "bad")

    def test_cleanup(self, workspace):
        wm = WorkspaceManager(base_dir=workspace)
        wm.create("task1")
        wm.write_file("task1", "test.py", "x")
        wm.cleanup("task1")
        assert not wm.exists("task1")

    def test_task_id_sanitization(self, workspace):
        wm = WorkspaceManager(base_dir=workspace)
        ws = wm.create("task/../escape")
        # path should be sanitized
        assert ".." not in str(ws)
