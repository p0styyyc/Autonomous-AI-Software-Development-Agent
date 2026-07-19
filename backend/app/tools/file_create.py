"""
FileCreateTool — 创建文件并写入内容

安全: 路径必须位于 workspace 内，自动创建父目录
"""

import logging
from pathlib import Path

from app.models.tool import FileCreateInput
from app.tools.base import WorkspaceAwareTool, ensure_directory

logger = logging.getLogger(__name__)


class FileCreateTool(WorkspaceAwareTool):
    """在 workspace 中创建文件并写入内容"""

    name: str = "file_create"
    description: str = (
        "Create a new file with specified content in the project workspace. "
        "Use this to create new source files, config files, or any other project files. "
        "Parent directories will be created automatically if they don't exist. "
        "Input: path (relative file path) and content (file contents as string)."
    )
    args_schema: type = FileCreateInput

    def _execute(self, path: str, content: str, encoding: str = "utf-8") -> str:
        """
        创建文件

        Args:
            path: workspace 内的相对路径
            content: 文件内容
            encoding: 文件编码，默认 utf-8
        """
        safe_path = self._validate_path(path)

        # 检查文件是否已存在
        if safe_path.exists():
            logger.warning(f"File already exists, overwriting: {safe_path}")
            action = "overwritten"
        else:
            action = "created"

        # 确保父目录存在
        ensure_directory(safe_path.parent)

        # 写入文件
        safe_path.write_text(content, encoding=encoding)

        size = safe_path.stat().st_size
        lines = content.count("\n") + 1

        logger.info(f"File {action}: {safe_path} ({size} bytes, {lines} lines)")
        return (
            f"[SUCCESS] File {action}: '{path}'\n"
            f"  Location: {safe_path}\n"
            f"  Size: {size} bytes | {lines} lines"
        )
