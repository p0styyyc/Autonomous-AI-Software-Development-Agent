"""
TestRunnerTool — 在 Docker 沙箱中运行测试

与 PythonExecutionTool 共用相同的沙箱安全机制。
额外功能: 解析 pytest 输出，提取通过/失败/总数。
"""

import logging
import re
import tempfile
import time
from pathlib import Path

from app.config import get_settings
from app.models.tool import TestRunnerInput
from app.tools.base import WorkspaceAwareTool
from app.tools.python_exec import _is_docker_available

logger = logging.getLogger(__name__)


class TestRunnerTool(WorkspaceAwareTool):
    """在 Docker 沙箱中运行 pytest 并返回结构化测试结果"""

    name: str = "run_tests"
    description: str = (
        "Run Python tests (pytest) in an isolated Docker sandbox. "
        "Provide all project files as a dict {path: content} and optionally a custom test command. "
        "Returns structured results: tests passed, failed, and total. "
        "Input: files (dict of file paths to contents), test_command (optional, default 'python -m pytest --tb=short'), "
        "timeout_seconds (optional, default 60)."
    )
    args_schema: type = TestRunnerInput

    def _execute(
        self,
        files: dict[str, str],
        test_command: str = "python -m pytest --tb=short",
        timeout_seconds: int = 60,
    ) -> str:
        settings = get_settings()

        if not _is_docker_available():
            return (
                "[DRY RUN] Docker not available — tests NOT executed.\n"
                f"  Would test {len(files)} files with command: {test_command}"
            )

        with tempfile.TemporaryDirectory(prefix="test_sandbox_") as tmp_dir:
            tmp_path = Path(tmp_dir)

            # 写入项目文件
            for file_path, file_content in files.items():
                safe_file = (tmp_path / file_path).resolve()
                try:
                    safe_file.relative_to(tmp_path.resolve())
                except ValueError:
                    return f"[SECURITY ERROR] File path '{file_path}' escapes sandbox directory"
                safe_file.parent.mkdir(parents=True, exist_ok=True)
                safe_file.write_text(file_content, encoding="utf-8")

            # 先安装 pytest（如果镜像中没有）
            full_cmd = f"pip install pytest -q 2>/dev/null; cd /sandbox && {test_command}"

            try:
                import docker

                client = docker.from_env()
                container = client.containers.run(
                    image=settings.sandbox_image,
                    command=["sh", "-c", full_cmd],
                    volumes={
                        str(tmp_path.resolve()): {
                            "bind": "/sandbox",
                            "mode": "ro",
                        }
                    },
                    network_mode="none",
                    mem_limit=settings.sandbox_memory_limit,
                    nano_cpus=int(settings.sandbox_cpu_limit * 1e9),
                    read_only=True,
                    tmpfs={"/tmp": "size=128m"},
                    security_opt=["no-new-privileges"],
                    cap_drop=["ALL"],
                    detach=True,
                )

                start_time = time.time()
                try:
                    result = container.wait(timeout=min(timeout_seconds, 300))
                    timed_out = False
                except Exception:
                    container.kill()
                    result = container.wait(timeout=5)
                    timed_out = True

                elapsed_ms = (time.time() - start_time) * 1000
                stdout = container.logs(stdout=True, stderr=False).decode("utf-8", errors="replace")
                stderr = container.logs(stdout=False, stderr=True).decode("utf-8", errors="replace")
                exit_code = result.get("StatusCode", -1)

                container.remove(force=True)

                # 解析 pytest 输出
                passed, failed, total = _parse_pytest_output(stdout + stderr)

                if timed_out:
                    return (
                        f"[TIMEOUT] Tests exceeded {timeout_seconds}s limit\n"
                        f"  Results: {passed}P / {failed}F / {total}T\n"
                        f"  Output:\n{_indent(stdout[:1000])}"
                    )

                status = "PASSED" if failed == 0 and exit_code == 0 else "FAILED"
                return (
                    f"[{status}] Tests completed ({elapsed_ms:.0f}ms)\n"
                    f"  Results: {passed} passed, {failed} failed, {total} total\n"
                    f"  Output:\n{_indent(stdout[:2000])}"
                )

            except Exception as e:
                logger.exception("Test sandbox execution failed")
                return f"[TEST RUNNER ERROR] {e}"


def _parse_pytest_output(output: str) -> tuple[int, int, int]:
    """
    解析 pytest 输出提取测试结果统计

    匹配模式:
      - "3 passed" / "1 failed" / "2 passed, 1 failed"
      - 短格式: "= 3 passed in 0.5s ="
    """
    passed = failed = 0

    # 模式 1: "X passed"
    m = re.search(r"(\d+)\s+passed", output)
    if m:
        passed = int(m.group(1))

    # 模式 2: "X failed"
    m = re.search(r"(\d+)\s+failed", output)
    if m:
        failed = int(m.group(1))

    # 模式 3: "X error"
    m = re.search(r"(\d+)\s+error", output)
    if m:
        failed += int(m.group(1))

    total = passed + failed
    return passed, failed, total


def _indent(text: str, spaces: int = 4) -> str:
    prefix = " " * spaces
    return prefix + text.replace("\n", f"\n{prefix}")
