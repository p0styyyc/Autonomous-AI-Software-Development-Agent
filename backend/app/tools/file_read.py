"""
FileReadTool — 读取文件内容

支持:
  - 完整读取
  - 按行范围读取 (start_line, end_line)
  - 自动语言检测
"""

import logging
from typing import Optional

from app.models.tool import FileReadInput
from app.tools.base import WorkspaceAwareTool, detect_language

logger = logging.getLogger(__name__)


class FileReadTool(WorkspaceAwareTool):
    """读取 workspace 中的文件内容，支持按行范围读取"""

    name: str = "file_read"
    description: str = (
        "Read the contents of a file in the project workspace. "
        "You can read the entire file or specify a line range with start_line and end_line (1-based, inclusive). "
        "Use this to understand existing code before modifying it. "
        "Input: path (relative file path), optional start_line and end_line."
    )
    args_schema: type = FileReadInput

    def _execute(
        self,
        path: str,
        start_line: Optional[int] = None,
        end_line: Optional[int] = None,
    ) -> str:
        safe_path = self._validate_path(path)

        if not safe_path.exists():
            return f"[ERROR] File not found: '{path}'"

        if not safe_path.is_file():
            return f"[ERROR] Path is not a file: '{path}'"

        try:
            content = safe_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            # 尝试其他编码
            try:
                content = safe_path.read_text(encoding="gbk")
            except Exception:
                return f"[ERROR] Cannot read file (encoding issue): '{path}'"

        lines = content.split("\n")
        total_lines = len(lines)

        # 按范围截取
        if start_line is not None or end_line is not None:
            start = max(1, start_line or 1) - 1  # 转 0-based
            end = min(total_lines, end_line or total_lines) if end_line else total_lines
            selected = lines[start:end]
            content = "\n".join(selected)
            range_info = f"lines {start + 1}-{end}"
        else:
            range_info = f"{total_lines} lines"

        language = detect_language(safe_path.name)

        # 格式化输出（带行号，方便 Agent 定位修改）
        numbered = "\n".join(
            f"{i + 1:>4}| {line}"
            for i, line in enumerate(content.split("\n"))
        )

        logger.info(f"File read: {safe_path} ({range_info}, {language})")
        return (
            f"[FILE] {path} ({range_info}, {language})\n"
            f"{'─' * 60}\n"
            f"{numbered}\n"
            f"{'─' * 60}"
        )
