"""
Workspace 管理服务 — 每个任务一个隔离的工作目录

职责:
  1. 创建/清理任务工作区
  2. 提供文件列表和内容摘要
  3. 管理工作区大小限制
"""

import logging
import shutil
from pathlib import Path
from typing import Optional

from app.config import get_settings

logger = logging.getLogger(__name__)


class WorkspaceManager:
    """
    工作区管理器

    每个 task_id 对应一个独立的子目录:
      workspace_base/{task_id}/

    使用示例:
        wm = WorkspaceManager()
        wm.create("abc123")
        wm.write_file("abc123", "main.py", "print('hello')")
        files = wm.list_files("abc123")
        wm.cleanup("abc123")
    """

    def __init__(self, base_dir: Optional[str] = None):
        settings = get_settings()
        self.base = Path(base_dir or settings.workspace_base_dir).resolve()
        self.max_size_mb = settings.max_workspace_size_mb

    def create(self, task_id: str) -> Path:
        """创建任务工作区"""
        ws = self._get_path(task_id)
        ws.mkdir(parents=True, exist_ok=True)
        logger.info(f"Workspace created: {ws}")
        return ws

    def exists(self, task_id: str) -> bool:
        """检查工作区是否存在"""
        return self._get_path(task_id).exists()

    def write_file(self, task_id: str, rel_path: str, content: str) -> Path:
        """
        在工作区写入文件

        Args:
            task_id: 任务 ID
            rel_path: 相对路径（不能包含 .. 遍历）
            content: 文件内容

        Returns:
            写入文件的绝对路径

        Raises:
            ValueError: 路径尝试逃逸工作区或超过大小限制
        """
        ws = self._get_path(task_id)
        file_path = (ws / rel_path).resolve()

        # 安全检查
        try:
            file_path.relative_to(ws)
        except ValueError:
            raise ValueError(f"Path traversal blocked: '{rel_path}'")

        # 大小检查
        content_size_mb = len(content.encode("utf-8")) / (1024 * 1024)
        if content_size_mb > self.max_size_mb:
            raise ValueError(
                f"File too large: {content_size_mb:.1f}MB (max {self.max_size_mb}MB)"
            )

        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")
        return file_path

    def read_file(self, task_id: str, rel_path: str) -> str:
        """读取工作区文件"""
        ws = self._get_path(task_id)
        file_path = (ws / rel_path).resolve()

        try:
            file_path.relative_to(ws)
        except ValueError:
            raise ValueError(f"Path traversal blocked: '{rel_path}'")

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {rel_path}")

        return file_path.read_text(encoding="utf-8")

    def list_files(self, task_id: str) -> list[str]:
        """列出工作区所有文件（相对路径）"""
        ws = self._get_path(task_id)
        if not ws.exists():
            return []

        files = []
        for f in ws.rglob("*"):
            if f.is_file() and not f.name.startswith("."):
                rel = str(f.relative_to(ws)).replace("\\", "/")
                files.append(rel)

        return sorted(files)

    def get_file_tree(self, task_id: str) -> str:
        """生成文件树字符串（给 Agent 看的）"""
        files = self.list_files(task_id)
        if not files:
            return "(empty workspace)"

        lines = []
        for f in files:
            depth = f.count("/")
            prefix = "  " * depth + ("└─ " if depth > 0 else "")
            lines.append(f"{prefix}{f.split('/')[-1] if '/' in f else f}")
        return "\n".join(lines)

    def get_workspace_summary(self, task_id: str) -> str:
        """
        生成工作区摘要（给 Coding Agent）

        包含文件树和每个文件的内容
        """
        files = self.list_files(task_id)
        if not files:
            return "(empty workspace — no files exist yet)"

        parts = [f"Workspace files ({len(files)} total):"]
        for f in files:
            try:
                content = self.read_file(task_id, f)
                # 截断长文件
                if len(content) > 2000:
                    content = content[:2000] + f"\n... ({len(content)} chars total, truncated)"
                parts.append(f"\n─── {f} ───\n{content}")
            except Exception as e:
                parts.append(f"\n─── {f} ───\n[ERROR reading file: {e}]")

        return "\n".join(parts)

    def cleanup(self, task_id: str) -> None:
        """删除任务工作区"""
        ws = self._get_path(task_id)
        if ws.exists():
            shutil.rmtree(ws)
            logger.info(f"Workspace cleaned: {ws}")

    def get_size(self, task_id: str) -> int:
        """获取工作区总大小（字节）"""
        ws = self._get_path(task_id)
        if not ws.exists():
            return 0
        return sum(f.stat().st_size for f in ws.rglob("*") if f.is_file())

    def _get_path(self, task_id: str) -> Path:
        """获取任务工作区路径"""
        # task_id 只保留安全的字符
        safe_id = "".join(c for c in task_id if c.isalnum() or c in "-_")
        return self.base / safe_id
