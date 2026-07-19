"""
FileModifyTool — 修改已有文件

支持 4 种操作:
  - replace:  精确替换 old_content → new_content
  - insert:   在指定行号后插入内容
  - append:   在文件末尾追加
  - delete_lines: 删除指定行范围
"""

import logging
from typing import Optional

from app.models.tool import FileModifyInput
from app.tools.base import WorkspaceAwareTool

logger = logging.getLogger(__name__)


class FileModifyTool(WorkspaceAwareTool):
    """修改 workspace 中已有文件的内容"""

    name: str = "file_modify"
    description: str = (
        "Modify an existing file in the project workspace. Supports 4 operations:\n"
        "  - replace: Replace old_content with new_content (exact match required)\n"
        "  - insert: Insert new_content after line_number\n"
        "  - append: Append new_content at the end of the file\n"
        "  - delete_lines: Delete count lines starting from line_number\n"
        "Input: path, operation, and the relevant content/line parameters."
    )
    args_schema: type = FileModifyInput

    def _execute(
        self,
        path: str,
        operation: str,
        old_content: Optional[str] = None,
        new_content: Optional[str] = None,
        line_number: Optional[int] = None,
        count: Optional[int] = None,
    ) -> str:
        safe_path = self._validate_path(path)

        if not safe_path.exists():
            return f"[ERROR] File not found: '{path}'"

        if not safe_path.is_file():
            return f"[ERROR] Path is not a file: '{path}'"

        content = safe_path.read_text(encoding="utf-8")
        original_content = content

        if operation == "replace":
            if old_content is None or new_content is None:
                return "[ERROR] 'replace' operation requires old_content and new_content"
            if old_content not in content:
                return (
                    f"[ERROR] old_content not found in file. "
                    f"Use file_read to check the exact content first."
                )
            content = content.replace(old_content, new_content, 1)

        elif operation == "insert":
            if new_content is None or line_number is None:
                return "[ERROR] 'insert' operation requires new_content and line_number"
            lines = content.split("\n")
            if line_number < 1 or line_number > len(lines) + 1:
                return f"[ERROR] line_number {line_number} out of range (1-{len(lines) + 1})"
            lines.insert(line_number, new_content)
            content = "\n".join(lines)

        elif operation == "append":
            if new_content is None:
                return "[ERROR] 'append' operation requires new_content"
            content = content.rstrip("\n") + "\n" + new_content + "\n"

        elif operation == "delete_lines":
            if line_number is None:
                return "[ERROR] 'delete_lines' operation requires line_number"
            lines = content.split("\n")
            delete_count = count or 1
            if line_number < 1 or line_number > len(lines):
                return f"[ERROR] line_number {line_number} out of range (1-{len(lines)})"
            end = min(line_number + delete_count - 1, len(lines))
            del lines[line_number - 1 : end]
            content = "\n".join(lines)

        else:
            return f"[ERROR] Unknown operation: '{operation}'. Supported: replace, insert, append, delete_lines"

        # 写入
        safe_path.write_text(content, encoding="utf-8")

        # 生成 diff 预览
        diff_preview = _generate_diff(original_content, content)

        logger.info(f"File modified: {safe_path} (operation={operation})")
        return (
            f"[SUCCESS] File modified: '{path}'\n"
            f"  Operation: {operation}\n"
            f"  Diff preview:\n{diff_preview}"
        )


def _generate_diff(original: str, modified: str, context_lines: int = 2) -> str:
    """生成简单的 unified diff 预览"""
    import difflib

    original_lines = original.split("\n")
    modified_lines = modified.split("\n")

    diff = list(
        difflib.unified_diff(
            original_lines,
            modified_lines,
            fromfile="a/original",
            tofile="b/modified",
            lineterm="",
            n=context_lines,
        )
    )

    if not diff:
        return "  (no changes)"

    # 限制预览长度
    preview = diff[:30]
    if len(diff) > 30:
        preview.append(f"  ... ({len(diff) - 30} more lines)")

    return "\n".join(f"  {line}" for line in preview)
