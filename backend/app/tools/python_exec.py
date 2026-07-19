"""
PythonExecutionTool — 在 Docker 沙箱中安全执行 Python 代码

安全设计 (5 层防护):
  1. Docker 容器隔离（非 subprocess）
  2. 网络完全禁用 (network_disabled)
  3. 只读根文件系统 (read_only=True)
  4. 内存限制 512MB + CPU 限制 1 核
  5. 30 秒超时强制终止

依赖: docker SDK (pip install docker)
如果 Docker 不可用，降级为 dry-run 模式（仅返回代码预览）
"""

import logging
import tempfile
import time
from pathlib import Path
from typing import Optional

from app.config import get_settings
from app.models.tool import PythonExecInput
from app.tools.base import WorkspaceAwareTool

logger = logging.getLogger(__name__)


class PythonExecutionTool(WorkspaceAwareTool):
    """
    在 Docker 沙箱中安全执行 Python 代码

    沙箱容器配置:
      - image: python:3.11-slim
      - 只读挂载项目文件
      - 网络完全隔离
      - 严格资源限制
      - 超时自动终止
    """

    name: str = "python_execute"
    description: str = (
        "Execute Python code in an isolated Docker sandbox. "
        "The code runs in a container with no network access, limited memory/CPU, and a strict timeout. "
        "Provide the code to execute and optionally a dict of project files {path: content} "
        "that will be written into the sandbox before execution. "
        "Input: code (Python code string), files (optional dict of file paths to contents), "
        "timeout_seconds (optional, default 30), entry_point (optional, default 'main.py')."
    )
    args_schema: type = PythonExecInput

    def _execute(
        self,
        code: str,
        files: Optional[dict[str, str]] = None,
        timeout_seconds: int = 30,
        entry_point: str = "main.py",
    ) -> str:
        """
        在 Docker 沙箱执行代码

        流程:
          1. 创建临时目录
          2. 写入所有项目文件
          3. 写入执行脚本
          4. 启动 Docker 容器执行
          5. 收集输出并清理
        """
        settings = get_settings()

        # 安全校验：先检查所有文件路径，防止路径遍历
        if files:
            for file_path in files:
                self._validate_path(file_path)

        # 检查 Docker 是否可用
        if not _is_docker_available():
            return self._dry_run(code, files)

        with tempfile.TemporaryDirectory(prefix="sandbox_") as tmp_dir:
            tmp_path = Path(tmp_dir)

            # 写入项目文件（已在上方通过 _validate_path 校验）
            if files:
                for file_path, file_content in files.items():
                    # 安全校验：文件路径必须在 tmp 内
                    safe_file = (tmp_path / file_path).resolve()
                    try:
                        safe_file.relative_to(tmp_path.resolve())
                    except ValueError:
                        return f"[SECURITY ERROR] File path '{file_path}' escapes sandbox directory"
                    safe_file.parent.mkdir(parents=True, exist_ok=True)
                    safe_file.write_text(file_content, encoding="utf-8")

            # 写入入口脚本
            entry_file = tmp_path / entry_point
            entry_file.write_text(code, encoding="utf-8")

            # 构建 Docker 命令
            cmd = f"cd /sandbox && python {entry_point}"

            try:
                import docker

                client = docker.from_env()
                container = client.containers.run(
                    image=settings.sandbox_image,
                    command=["sh", "-c", cmd],
                    volumes={
                        str(tmp_path.resolve()): {
                            "bind": "/sandbox",
                            "mode": "ro",  # 只读挂载
                        }
                    },
                    network_mode="none" if settings.sandbox_network_disabled else "bridge",
                    mem_limit=settings.sandbox_memory_limit,
                    nano_cpus=int(settings.sandbox_cpu_limit * 1e9),
                    read_only=True,
                    tmpfs={"/tmp": "size=64m"},
                    security_opt=["no-new-privileges"],
                    cap_drop=["ALL"],
                    detach=True,
                )

                start_time = time.time()
                try:
                    result = container.wait(
                        timeout=min(timeout_seconds, settings.sandbox_timeout_seconds)
                    )
                    timed_out = False
                except Exception:
                    # 超时
                    container.kill()
                    result = container.wait(timeout=5)
                    timed_out = True

                elapsed_ms = (time.time() - start_time) * 1000
                stdout = container.logs(stdout=True, stderr=False).decode("utf-8", errors="replace")
                stderr = container.logs(stdout=False, stderr=True).decode("utf-8", errors="replace")
                exit_code = result.get("StatusCode", -1)

                container.remove(force=True)

                if timed_out:
                    return (
                        f"[TIMEOUT] Code execution exceeded {timeout_seconds}s limit\n"
                        f"  Stdout:\n{_indent(stdout or '(none)')}\n"
                        f"  Stderr:\n{_indent(stderr or '(none)')}"
                    )

                if exit_code == 0:
                    return (
                        f"[SUCCESS] Code executed successfully ({elapsed_ms:.0f}ms)\n"
                        f"  Stdout:\n{_indent(stdout or '(no output)')}"
                    )
                else:
                    return (
                        f"[ERROR] Code exited with code {exit_code} ({elapsed_ms:.0f}ms)\n"
                        f"  Stdout:\n{_indent(stdout or '(none)')}\n"
                        f"  Stderr:\n{_indent(stderr or '(none)')}"
                    )

            except Exception as e:
                logger.exception("Docker sandbox execution failed")
                return f"[SANDBOX ERROR] {e}"

    def _dry_run(self, code: str, files: Optional[dict[str, str]] = None) -> str:
        """Docker 不可用时的降级模式：仅预览代码"""
        file_list = "\n".join(f"  - {f}" for f in (files or {}).keys()) if files else "  (none)"
        return (
            f"[DRY RUN] Docker not available — code NOT executed.\n"
            f"  Files: {len(files or {})} files\n{file_list}\n"
            f"  Code preview ({len(code)} chars):\n{_indent(code[:500])}"
        )


def _is_docker_available() -> bool:
    """检查 Docker SDK 和守护进程是否可用"""
    try:
        import docker
        client = docker.from_env()
        client.ping()
        return True
    except Exception:
        return False


def _indent(text: str, spaces: int = 4) -> str:
    """文本缩进辅助"""
    prefix = " " * spaces
    return prefix + text.replace("\n", f"\n{prefix}")
