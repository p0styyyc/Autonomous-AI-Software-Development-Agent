"""
Tool Registry — 工具注册与按角色分发

设计模式: Registry Pattern + 依赖注入
  - 所有 Tool 在注册表中统一管理
  - 按 Agent 角色返回不同工具集（最小权限原则）
  - Tool 需要 workspace_path 参数，在初始化时注入
"""

import logging
from dataclasses import dataclass, field
from typing import Optional

from langchain_core.tools import BaseTool

from app.tools.file_create import FileCreateTool
from app.tools.file_read import FileReadTool
from app.tools.file_modify import FileModifyTool
from app.tools.python_exec import PythonExecutionTool
from app.tools.test_runner import TestRunnerTool

logger = logging.getLogger(__name__)


@dataclass
class ToolRegistry:
    """
    工具注册表

    使用方式:
        registry = ToolRegistry(workspace_path="/tmp/workspace")
        coder_tools = registry.for_coder()       # 文件操作工具
        executor_tools = registry.for_executor()  # 执行工具
        all_tools = registry.all()                # 全部工具
    """

    workspace_path: str

    # 延迟初始化（dataclass default_factory）
    _file_create: Optional[FileCreateTool] = field(default=None, init=False, repr=False)
    _file_read: Optional[FileReadTool] = field(default=None, init=False, repr=False)
    _file_modify: Optional[FileModifyTool] = field(default=None, init=False, repr=False)
    _python_exec: Optional[PythonExecutionTool] = field(default=None, init=False, repr=False)
    _test_runner: Optional[TestRunnerTool] = field(default=None, init=False, repr=False)

    def _get(self, name: str) -> BaseTool:
        """延迟初始化获取 Tool 实例"""
        if name == "file_create":
            if self._file_create is None:
                self._file_create = FileCreateTool(workspace_path=self.workspace_path)
            return self._file_create

        if name == "file_read":
            if self._file_read is None:
                self._file_read = FileReadTool(workspace_path=self.workspace_path)
            return self._file_read

        if name == "file_modify":
            if self._file_modify is None:
                self._file_modify = FileModifyTool(workspace_path=self.workspace_path)
            return self._file_modify

        if name == "python_execute":
            if self._python_exec is None:
                self._python_exec = PythonExecutionTool(workspace_path=self.workspace_path)
            return self._python_exec

        if name == "run_tests":
            if self._test_runner is None:
                self._test_runner = TestRunnerTool(workspace_path=self.workspace_path)
            return self._test_runner

        raise KeyError(f"Unknown tool: {name}")

    def for_planner(self) -> list[BaseTool]:
        """Planner Agent 工具: 只需读取文件了解项目状态"""
        return [self._get("file_read")]

    def for_coder(self) -> list[BaseTool]:
        """Coding Agent 工具: 文件 CRUD"""
        return [
            self._get("file_create"),
            self._get("file_read"),
            self._get("file_modify"),
        ]

    def for_executor(self) -> list[BaseTool]:
        """Execution Agent 工具: 执行代码和测试"""
        return [
            self._get("python_execute"),
            self._get("run_tests"),
            self._get("file_read"),  # 读取执行输出
        ]

    def for_reviewer(self) -> list[BaseTool]:
        """Reviewer Agent 工具: 只需读取代码"""
        return [self._get("file_read")]

    def all(self) -> list[BaseTool]:
        """所有工具（调试用）"""
        return [
            self._get("file_create"),
            self._get("file_read"),
            self._get("file_modify"),
            self._get("python_execute"),
            self._get("run_tests"),
        ]

    def get_by_name(self, name: str) -> BaseTool:
        """按名称获取单个工具"""
        return self._get(name)

    @property
    def tool_names(self) -> list[str]:
        """所有注册的工具名称"""
        return ["file_create", "file_read", "file_modify", "python_execute", "run_tests"]


def create_tool_registry(workspace_path: str) -> ToolRegistry:
    """工厂函数：创建工具注册表"""
    logger.info(f"Creating tool registry for workspace: {workspace_path}")
    return ToolRegistry(workspace_path=workspace_path)
