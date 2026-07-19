"""ToolRegistry 单元测试"""

import pytest
from app.tools.registry import ToolRegistry, create_tool_registry


class TestToolRegistry:
    """ToolRegistry 测试套件"""

    def test_create_registry(self, workspace):
        """测试创建注册表"""
        reg = create_tool_registry(workspace)
        assert len(reg.tool_names) == 5
        assert "file_create" in reg.tool_names
        assert "python_execute" in reg.tool_names

    def test_coder_tools(self, workspace):
        """测试 Coder 工具集"""
        reg = ToolRegistry(workspace_path=workspace)
        tools = reg.for_coder()
        names = [t.name for t in tools]
        assert "file_create" in names
        assert "file_read" in names
        assert "file_modify" in names
        assert "python_execute" not in names  # Coder 不需要执行权限

    def test_executor_tools(self, workspace):
        """测试 Executor 工具集"""
        reg = ToolRegistry(workspace_path=workspace)
        tools = reg.for_executor()
        names = [t.name for t in tools]
        assert "python_execute" in names
        assert "run_tests" in names

    def test_reviewer_tools_minimal(self, workspace):
        """测试 Reviewer 只有只读权限"""
        reg = ToolRegistry(workspace_path=workspace)
        tools = reg.for_reviewer()
        names = [t.name for t in tools]
        assert names == ["file_read"]  # 最小权限原则

    def test_planner_tools_minimal(self, workspace):
        """测试 Planner 只有只读权限"""
        reg = ToolRegistry(workspace_path=workspace)
        tools = reg.for_planner()
        names = [t.name for t in tools]
        assert names == ["file_read"]

    def test_get_by_name(self, workspace):
        """测试按名称获取工具"""
        reg = ToolRegistry(workspace_path=workspace)
        tool = reg.get_by_name("file_create")
        assert tool.name == "file_create"

    def test_unknown_tool_raises(self, workspace):
        """测试获取未知工具抛出异常"""
        reg = ToolRegistry(workspace_path=workspace)
        with pytest.raises(KeyError):
            reg.get_by_name("nonexistent_tool")

    def test_tools_share_workspace(self, workspace):
        """测试所有工具共享同一个 workspace"""
        reg = ToolRegistry(workspace_path=workspace)
        for tool in reg.all():
            assert tool.workspace_path == workspace
