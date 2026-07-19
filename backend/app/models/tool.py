"""
Tool 输入/输出模型 — 定义所有 Agent Tool 的标准化接口

每个 Tool 的输入和输出都使用 Pydantic 严格校验，
确保 Agent 调用 Tool 时参数正确。
"""

from typing import Optional

from pydantic import BaseModel, Field


# ═══════════════════════════════════════════════
# FileCreateTool
# ═══════════════════════════════════════════════

class FileCreateInput(BaseModel):
    """FileCreateTool 输入"""
    path: str = Field(..., description="文件路径（相对于 workspace 根目录）")
    content: str = Field(..., description="文件内容")
    encoding: str = Field(default="utf-8", description="文件编码")


class FileCreateOutput(BaseModel):
    """FileCreateTool 输出"""
    success: bool
    path: str
    size_bytes: int
    message: str


# ═══════════════════════════════════════════════
# FileReadTool
# ═══════════════════════════════════════════════

class FileReadInput(BaseModel):
    """FileReadTool 输入"""
    path: str = Field(..., description="要读取的文件路径")
    start_line: Optional[int] = Field(default=None, ge=1, description="起始行号（1-based）")
    end_line: Optional[int] = Field(default=None, ge=1, description="结束行号（1-based）")


class FileReadOutput(BaseModel):
    """FileReadTool 输出"""
    success: bool
    path: str
    content: str = ""
    total_lines: int = 0
    language: str = ""
    message: str = ""


# ═══════════════════════════════════════════════
# FileModifyTool
# ═══════════════════════════════════════════════

class FileModifyInput(BaseModel):
    """FileModifyTool 输入"""
    path: str = Field(..., description="要修改的文件路径")
    operation: str = Field(
        ...,
        pattern="^(replace|insert|append|delete_lines)$",
        description="操作类型: replace/insert/append/delete_lines",
    )
    old_content: Optional[str] = Field(default=None, description="替换操作：旧内容")
    new_content: Optional[str] = Field(default=None, description="替换/插入操作：新内容")
    line_number: Optional[int] = Field(default=None, ge=1, description="插入/删除行号")
    count: Optional[int] = Field(default=None, ge=1, description="删除操作：行数")


class FileModifyOutput(BaseModel):
    """FileModifyTool 输出"""
    success: bool
    path: str
    operation: str
    message: str
    diff_preview: str = ""


# ═══════════════════════════════════════════════
# PythonExecutionTool
# ═══════════════════════════════════════════════

class PythonExecInput(BaseModel):
    """PythonExecutionTool 输入"""
    code: str = Field(..., description="要执行的 Python 代码")
    files: dict[str, str] = Field(
        default_factory=dict,
        description="项目文件 {path: content}，会写入沙箱后执行代码",
    )
    timeout_seconds: int = Field(
        default=30,
        ge=1,
        le=300,
        description="执行超时（秒）",
    )
    entry_point: str = Field(
        default="main.py",
        description="执行的入口文件",
    )


class PythonExecOutput(BaseModel):
    """PythonExecutionTool 输出"""
    exit_code: int
    stdout: str
    stderr: str
    execution_time_ms: float
    timed_out: bool
    success: bool

    @property
    def is_success(self) -> bool:
        return self.exit_code == 0 and not self.timed_out


# ═══════════════════════════════════════════════
# TestRunnerTool
# ═══════════════════════════════════════════════

class TestRunnerInput(BaseModel):
    """TestRunnerTool 输入"""
    files: dict[str, str] = Field(..., description="项目文件 {path: content}")
    test_command: str = Field(
        default="python -m pytest --tb=short",
        description="测试执行命令",
    )
    timeout_seconds: int = Field(default=60, ge=1, le=300)


class TestRunnerOutput(BaseModel):
    """TestRunnerTool 输出"""
    exit_code: int
    stdout: str
    stderr: str
    tests_passed: int = 0
    tests_failed: int = 0
    tests_total: int = 0
    execution_time_ms: float = 0
    timed_out: bool = False
