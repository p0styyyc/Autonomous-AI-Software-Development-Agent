"""
Agent 状态定义 — LangGraph StateGraph 的核心数据结构

每个 Agent Node 读取和写入同一个 State 对象，
State 在整个流水线中流动，实现 Agent 间信息传递。
"""

from typing import Annotated, Any, Literal, Optional, TypedDict

from langgraph.graph.message import add_messages


class Step(TypedDict):
    """单个执行步骤"""
    id: int
    description: str
    files_to_create: list[str]
    files_to_modify: list[str]
    expected_output: str
    complexity: int  # 1-5
    depends_on: list[int]  # 依赖的步骤 ID


class ExecutionResult(TypedDict):
    """代码执行结果"""
    exit_code: int
    stdout: str
    stderr: str
    execution_time_ms: float
    timed_out: bool


class ReviewResult(TypedDict):
    """代码审查结果"""
    passed: bool
    score: int  # 0-100
    issues: list[str]
    suggestions: list[str]
    summary: str


class AgentState(TypedDict):
    """
    LangGraph Agent 全局状态

    每个字段都有明确的来源和修改者，便于追踪数据流向:
    - 规划阶段写入: plan, steps
    - 编码阶段写入: files_created, files_modified
    - 执行阶段写入: execution_result
    - 审查阶段写入: review_result
    - 编排器维护: current_step_index, retry_count, status
    """

    # ── 任务标识 ──────────────────────────────
    task_id: str
    user_request: str

    # ── 消息历史 (LangGraph 内置消息管理) ─────
    # add_messages reducer 会自动合并消息列表，而不是覆盖
    messages: Annotated[list, add_messages]

    # ── 计划 ──────────────────────────────────
    plan_summary: str
    steps: list[Step]
    current_step_index: int

    # ── 代码变更 ──────────────────────────────
    workspace_path: str
    files_created: list[str]
    files_modified: list[str]

    # ── 执行与审查 ────────────────────────────
    execution_result: Optional[ExecutionResult]
    review_result: Optional[ReviewResult]

    # ── 重试控制 ──────────────────────────────
    retry_count: int
    max_retries: int

    # ── 结果 ──────────────────────────────────
    final_report: Optional[str]
    status: str  # pending | planning | coding | executing | reviewing | done | failed
    error_message: Optional[str]

    # ── Provider 配置 ─────────────────────────
    provider: str
    model: str


# ── 状态工厂函数 ──────────────────────────────

def create_initial_state(
    task_id: str,
    user_request: str,
    provider: str = "openai",
    model: str = "gpt-4o-mini",
    max_retries: int = 3,
) -> AgentState:
    """创建初始 AgentState，用于 LangGraph 的 entry point"""
    return AgentState(
        task_id=task_id,
        user_request=user_request,
        messages=[],
        plan_summary="",
        steps=[],
        current_step_index=0,
        workspace_path="",
        files_created=[],
        files_modified=[],
        execution_result=None,
        review_result=None,
        retry_count=0,
        max_retries=max_retries,
        final_report=None,
        status="pending",
        error_message=None,
        provider=provider,
        model=model,
    )
