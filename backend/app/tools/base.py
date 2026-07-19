"""
Tool 基类 — 所有 Agent Tool 的抽象基类

职责:
  1. 统一路径安全校验（防止路径遍历攻击）
  2. 统一异常处理和日志
  3. 提供 Tool 元数据（name, description, args_schema）

安全设计:
  所有文件操作限制在 workspace_path 内。
  使用 resolve() + is_relative_to() 防止 ../ 路径遍历。
"""

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from langchain_core.tools import BaseTool
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class PathSecurityError(ValueError):
    """路径安全异常 — 当访问 workspace 外的路径时抛出"""
    pass


class WorkspaceAwareTool(BaseTool, ABC):
    """
    工作区感知的 Tool 基类

    子类自动获得:
      - _validate_path(): 路径安全校验
      - _resolve_path(): 安全解析路径到 workspace 内
      - 统一的 _run() 错误处理
    """

    workspace_path: str = ""

    model_config = {"arbitrary_types_allowed": True}

    def _validate_path(self, relative_path: str) -> Path:
        """
        校验并返回 workspace 内的安全绝对路径

        防御策略:
          1. 使用 resolve() 消除 .. 符号链接等
          2. 使用 is_relative_to() 确保路径在 workspace 内（Python 3.9+ 无此方法，用备选方案）

        Args:
            relative_path: 用户提供的相对路径

        Returns:
            安全的绝对路径

        Raises:
            PathSecurityError: 路径试图逃逸 workspace
            ValueError: workspace_path 未设置
        """
        if not self.workspace_path:
            raise ValueError("workspace_path is not set. Tool must be initialized with a workspace.")

        workspace = Path(self.workspace_path).resolve()
        target = (workspace / relative_path).resolve()

        # Python <3.9 兼容的路径包含检查
        try:
            target.relative_to(workspace)
        except ValueError:
            raise PathSecurityError(
                f"Path traversal detected: '{relative_path}' resolves outside workspace. "
                f"Workspace: {workspace}, Resolved: {target}"
            )

        return target

    def _run(self, **kwargs) -> str:
        """
        统一入口 — 子类实现 _execute() 而非 _run()

        捕获所有异常并返回格式化字符串，确保 Agent 总能得到可读输出
        """
        try:
            result = self._execute(**kwargs)
            return result
        except PathSecurityError as e:
            logger.warning(f"Path security violation: {e}")
            return f"SECURITY ERROR: {e}"
        except Exception as e:
            logger.exception(f"Tool '{self.name}' failed")
            return f"TOOL ERROR [{self.name}]: {type(e).__name__}: {e}"

    @abstractmethod
    def _execute(self, **kwargs) -> str:
        """
        子类实现具体逻辑（替代 _run）

        返回: 格式化字符串结果，供 LLM 阅读
        """
        ...


def ensure_directory(path: Path) -> None:
    """确保目录存在，不存在则创建"""
    path.mkdir(parents=True, exist_ok=True)


def detect_language(file_path: str) -> str:
    """根据文件扩展名检测编程语言"""
    ext_to_lang = {
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".jsx": "jsx",
        ".tsx": "tsx",
        ".html": "html",
        ".css": "css",
        ".json": "json",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".md": "markdown",
        ".txt": "text",
        ".sh": "bash",
        ".sql": "sql",
        ".rs": "rust",
        ".go": "go",
        ".java": "java",
        ".cpp": "cpp",
        ".c": "c",
        ".h": "c",
        ".rb": "ruby",
        ".php": "php",
        ".xml": "xml",
        ".toml": "toml",
        ".cfg": "ini",
        ".ini": "ini",
        ".env": "text",
        ".dockerfile": "dockerfile",
        ".gitignore": "text",
        ".csv": "csv",
    }
    ext = Path(file_path).suffix.lower()
    # 处理无扩展名的特殊文件
    filename = Path(file_path).name.lower()
    if filename == "dockerfile":
        return "dockerfile"
    if filename == "makefile":
        return "makefile"
    return ext_to_lang.get(ext, "text")
