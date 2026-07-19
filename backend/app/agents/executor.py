"""
Execution Agent — 代码执行与测试运行

职责:
  1. 收集当前步骤产出的所有代码文件
  2. 在 Docker 沙箱中执行入口脚本
  3. 运行测试（如果有）
  4. 返回结构化的执行结果

安全:
  所有代码在 Docker 容器中执行，不直接调用 subprocess
"""

import logging
from pathlib import Path
from typing import Optional

from langchain_core.language_models import BaseChatModel

from app.agents.base import AgentBase
from app.models.tool import PythonExecInput, PythonExecOutput
from app.tools.python_exec import PythonExecutionTool

logger = logging.getLogger(__name__)

EXECUTOR_SYSTEM_PROMPT = """You are a Code Execution Specialist. Your job is to:

1. Read the code files that were created/modified in the current step
2. Execute the code in an isolated sandbox environment
3. Analyze the execution results (stdout, stderr, exit code)
4. Report whether the execution was successful

## Output Format

Provide a clear execution report:
- **Status**: SUCCESS or FAILURE
- **Exit Code**: the numeric exit code
- **Stdout**: key output lines
- **Stderr**: any error messages
- **Analysis**: why it succeeded or failed, in plain language
"""


class ExecutionAgent(AgentBase):
    """代码执行 Agent — 在沙箱中运行代码并分析结果"""

    name: str = "executor"

    def __init__(self, llm, tools=None, verbose=False, workspace_path: str = ""):
        super().__init__(llm=llm, tools=tools, verbose=verbose)
        self.workspace_path = workspace_path
        self._python_tool = PythonExecutionTool(workspace_path=workspace_path)

    @property
    def system_prompt(self) -> str:
        return EXECUTOR_SYSTEM_PROMPT

    def execute(
        self,
        code_files: dict[str, str],
        entry_point: str = "main.py",
        timeout_seconds: int = 30,
    ) -> PythonExecOutput:
        """
        在沙箱中执行代码

        Args:
            code_files: {文件路径: 文件内容} 的字典
            entry_point: 入口文件名
            timeout_seconds: 执行超时

        Returns:
            PythonExecOutput: 结构化执行结果
        """
        logger.info(
            f"[Executor] Executing {len(code_files)} files, entry={entry_point}"
        )

        # 自动检测入口文件：如果指定的入口不存在，查找其他 Python 文件
        actual_entry = entry_point
        if entry_point not in code_files:
            py_files = sorted([
                f for f in code_files
                if f.endswith(".py") and not f.startswith("test_")
            ])
            # 优先选择常见入口文件名
            for candidate in ["main.py", "app.py", "server.py", "run.py", "cli.py"]:
                if candidate in py_files:
                    actual_entry = candidate
                    break
            if actual_entry == entry_point and py_files:
                actual_entry = py_files[0]

        if actual_entry not in code_files:
            file_list = ", ".join(list(code_files.keys())[:10])
            return PythonExecOutput(
                exit_code=-1,
                stdout="",
                stderr=f"No Python entry file found. Available files: {file_list}",
                execution_time_ms=0,
                timed_out=False,
                success=False,
            )

        # 使用 PythonExecutionTool 在沙箱中执行
        result_str = self._python_tool._run(
            code=code_files[actual_entry],
            files=code_files,
            timeout_seconds=timeout_seconds,
            entry_point=actual_entry,
        )

        return self._parse_result(result_str)

    def execute_and_analyze(
        self,
        code_files: dict[str, str],
        step_description: str,
        expected_output: str = "",
        entry_point: str = "main.py",
    ) -> str:
        """
        执行代码并用 LLM 分析结果

        Args:
            code_files: 代码文件字典
            step_description: 当前步骤描述
            expected_output: 预期输出（来自 Planner）
            entry_point: 入口文件

        Returns:
            LLM 分析报告
        """
        result = self.execute(code_files, entry_point)

        analysis_prompt = f"""## Step Description
{step_description}

## Expected Output
{expected_output or 'Not specified'}

## Execution Result
- Exit Code: {result.exit_code}
- Timed Out: {result.timed_out}
- Execution Time: {result.execution_time_ms:.0f}ms

### Stdout:
```
{result.stdout or '(no output)'}
```

### Stderr:
```
{result.stderr or '(no errors)'}
```

## Your Analysis
Please analyze the execution result. Did it succeed? Does it match the expected output?
What should be fixed if it failed?
"""

        return self.invoke(analysis_prompt)

    def _parse_result(self, raw: str) -> PythonExecOutput:
        """将 PythonExecutionTool 的字符串输出解析为结构化对象"""
        if "SUCCESS" in raw:
            # 提取 exit code 和 stdout
            return PythonExecOutput(
                exit_code=0,
                stdout=raw,
                stderr="",
                execution_time_ms=0,
                timed_out=False,
                success=True,
            )
        elif "TIMEOUT" in raw:
            return PythonExecOutput(
                exit_code=-1,
                stdout="",
                stderr=raw,
                execution_time_ms=0,
                timed_out=True,
                success=False,
            )
        elif "DRY RUN" in raw:
            return PythonExecOutput(
                exit_code=0,
                stdout=raw,
                stderr="",
                execution_time_ms=0,
                timed_out=False,
                success=True,
            )
        else:
            return PythonExecOutput(
                exit_code=1,
                stdout="",
                stderr=raw,
                execution_time_ms=0,
                timed_out=False,
                success=False,
            )


def collect_workspace_files(workspace_path: str) -> dict[str, str]:
    """收集 workspace 中所有文件的内容"""
    files = {}
    ws = Path(workspace_path)
    if not ws.exists():
        return files

    for file_path in ws.rglob("*"):
        if file_path.is_file():
            relative = str(file_path.relative_to(ws)).replace("\\", "/")
            try:
                files[relative] = file_path.read_text(encoding="utf-8")
            except Exception:
                files[relative] = f"[binary or unreadable: {file_path.suffix}]"

    return files
