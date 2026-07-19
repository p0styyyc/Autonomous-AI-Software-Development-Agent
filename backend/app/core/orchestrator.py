"""
LangGraph Orchestrator — 多 Agent 流水线编排器

核心流程:
    START → planner → coder → executor → reviewer
                  ↑         ↑                    │
                  │         └── retry ───────────┤ (failed, retry < max)
                  │                              │
                  └── next step ─────────────────┘ (passed or max retries)
                                                      │
                                                     END

使用 LangGraph StateGraph 实现：
  - 每个 Agent 对应一个 Node
  - 条件路由决定下一步（重试 or 继续 or 结束）
  - State 在 Node 间传递，积累执行结果
"""

import logging
from typing import Literal

from langgraph.graph import END, StateGraph
from langgraph.checkpoint.memory import MemorySaver

from app.agents.base import AgentBase
from app.agents.coder import CodingAgent
from app.agents.executor import ExecutionAgent, collect_workspace_files
from app.agents.planner import PlannerAgent
from app.agents.reviewer import ReviewAgent
from app.config import get_settings
from app.core.llm import (
    create_llm,
    create_coder_llm,
    create_planner_llm,
    create_reviewer_llm,
)
from app.core.state import AgentState, create_initial_state
from app.models.ws_event import WSEvent
from app.services.event_bus import EventBus, get_event_bus
from app.services.workspace import WorkspaceManager
from app.tools.registry import create_tool_registry

logger = logging.getLogger(__name__)


class AgentOrchestrator:
    """
    Agent 流水线编排器

    使用 LangGraph StateGraph 管理 4 个 Agent 的执行顺序和条件路由。

    使用示例:
        orchestrator = AgentOrchestrator()
        result = await orchestrator.run("创建天气查询API")
    """

    def __init__(
        self,
        workspace: WorkspaceManager | None = None,
        event_bus: EventBus | None = None,
    ):
        self.settings = get_settings()
        self.workspace = workspace or WorkspaceManager()
        self.event_bus = event_bus or get_event_bus()
        self._graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """构建 LangGraph 状态图"""
        workflow = StateGraph(AgentState)

        # 添加 Node
        workflow.add_node("planner", self._planner_node)
        workflow.add_node("coder", self._coder_node)
        workflow.add_node("executor", self._executor_node)
        workflow.add_node("reviewer", self._reviewer_node)
        workflow.add_node("finalize", self._finalize_node)

        # 设置入口
        workflow.set_entry_point("planner")

        # 添加边
        workflow.add_edge("planner", "coder")

        # Coder → Executor（执行代码）
        workflow.add_edge("coder", "executor")

        # Executor → Reviewer（审查结果）
        workflow.add_edge("executor", "reviewer")

        # Reviewer → 条件路由（重试 or 继续 or 结束）
        workflow.add_conditional_edges(
            "reviewer",
            self._route_after_review,
            {
                "retry": "coder",
                "next_step": "coder",
                "finalize": "finalize",
            },
        )

        # Finalize → END
        workflow.add_edge("finalize", END)

        # 编译（带内存检查点，支持状态恢复）
        return workflow.compile(checkpointer=MemorySaver())

    # ── Node 实现 ──────────────────────────────

    async def _planner_node(self, state: AgentState) -> dict:
        """Planner Node: 分析需求，制定计划"""
        self._emit(state, "planning_started")

        try:
            llm = create_planner_llm()
            planner = PlannerAgent(llm=llm)

            plan = planner.plan(state["user_request"])

            self._emit(
                state,
                "planning_completed",
                task_summary=plan["task_summary"],
                steps_count=len(plan["steps"]),
                tech_stack=plan.get("tech_stack", {}),
            )

            return {
                "plan_summary": plan["task_summary"],
                "steps": plan["steps"],
                "current_step_index": 0,
                "status": "coding",
                "files_created": [],
                "files_modified": [],
            }
        except Exception as e:
            logger.exception("Planner node failed")
            return {
                "status": "failed",
                "error_message": f"Planning failed: {e}",
            }

    async def _coder_node(self, state: AgentState) -> dict:
        """Coder Node: 根据当前步骤生成/修改代码"""
        steps = state["steps"]
        step_idx = state["current_step_index"]

        if step_idx >= len(steps):
            return {"status": "done"}

        step = steps[step_idx]

        self._emit(
            state,
            "step_started",
            step_id=step["id"],
            description=step["description"],
            step_index=step_idx,
            total_steps=len(steps),
        )
        self._emit(state, "coding_started", step_id=step["id"])

        try:
            # 准备 Coder
            llm = create_coder_llm()
            tool_registry = create_tool_registry(str(self.workspace._get_path(state["task_id"])))
            coder = CodingAgent(llm=llm, tools=tool_registry.for_coder())

            # 获取工作区现状
            workspace_summary = self.workspace.get_workspace_summary(state["task_id"])

            # 执行代码生成
            result = coder.implement_step(
                task_summary=state["plan_summary"],
                step=step,
                workspace_state=workspace_summary,
            )

            # 更新文件列表
            files_created = list(state.get("files_created", []))
            files_modified = list(state.get("files_modified", []))
            for f in step.get("files_to_create", []):
                if f not in files_created:
                    files_created.append(f)
            for f in step.get("files_to_modify", []):
                if f not in files_modified:
                    files_modified.append(f)

            self._emit(
                state,
                "code_generated",
                step_id=step["id"],
                files_created=step.get("files_to_create", []),
                files_modified=step.get("files_to_modify", []),
            )

            return {
                "files_created": files_created,
                "files_modified": files_modified,
                "status": "executing",
            }

        except Exception as e:
            logger.exception("Coder node failed")
            self._emit(state, "error", message=f"Coding failed: {e}")
            return {
                "error_message": f"Coding failed: {e}",
            }

    async def _executor_node(self, state: AgentState) -> dict:
        """Executor Node: 在沙箱中执行代码"""
        self._emit(state, "executing_started")

        try:
            # 收集工作区文件
            code_files = collect_workspace_files(
                str(self.workspace._get_path(state["task_id"]))
            )

            if not code_files:
                return {
                    "execution_result": {
                        "exit_code": -1,
                        "stdout": "",
                        "stderr": "No files to execute",
                        "execution_time_ms": 0,
                        "timed_out": False,
                    },
                    "status": "reviewing",
                }

            # 在沙箱中执行
            llm = create_llm()
            executor = ExecutionAgent(
                llm=llm,
                workspace_path=str(self.workspace._get_path(state["task_id"])),
            )

            result = executor.execute(
                code_files=code_files,
                entry_point="main.py",
                timeout_seconds=self.settings.sandbox_timeout_seconds,
            )

            execution_data = {
                "exit_code": result.exit_code,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "execution_time_ms": result.execution_time_ms,
                "timed_out": result.timed_out,
            }

            if result.success:
                self._emit(state, "execution_success", **execution_data)
            else:
                self._emit(state, "execution_error", **execution_data)

            return {
                "execution_result": execution_data,
                "status": "reviewing",
            }

        except Exception as e:
            logger.exception("Executor node failed")
            return {
                "execution_result": {
                    "exit_code": -1,
                    "stdout": "",
                    "stderr": str(e),
                    "execution_time_ms": 0,
                    "timed_out": False,
                },
                "status": "reviewing",
            }

    async def _reviewer_node(self, state: AgentState) -> dict:
        """Reviewer Node: 审查代码质量和执行结果"""
        step_idx = state["current_step_index"]
        step = state["steps"][step_idx]
        self._emit(state, "reviewing_started", step_id=step["id"])

        try:
            llm = create_reviewer_llm()
            reviewer = ReviewAgent(llm=llm)

            # 收集代码
            workspace_summary = self.workspace.get_workspace_summary(state["task_id"])

            # 格式化执行结果
            exec_result = state.get("execution_result", {})
            exec_str = (
                f"Exit Code: {exec_result.get('exit_code', '?')}\n"
                f"Stdout: {exec_result.get('stdout', '')[:1000]}\n"
                f"Stderr: {exec_result.get('stderr', '')[:1000]}\n"
                f"Timed Out: {exec_result.get('timed_out', False)}"
            )

            review = reviewer.review(
                step_description=step["description"],
                expected_output=step.get("expected_output", ""),
                code=workspace_summary[:8000],
                execution_result=exec_str,
            )

            review_data = {
                "passed": review["passed"],
                "overall_score": review["overall_score"],
                "dimensions": review.get("dimensions", {}),
                "critical_issues": review.get("critical_issues", []),
                "suggestions": review.get("suggestions", []),
                "summary": review.get("summary", ""),
            }

            if review["passed"]:
                self._emit(state, "review_pass", **review_data)
            else:
                self._emit(state, "review_fail", **review_data)

            return {"review_result": review_data}

        except Exception as e:
            logger.exception("Reviewer node failed")
            return {
                "review_result": {
                    "passed": True,  # 审查异常时默认通过，避免死循环
                    "overall_score": 0,
                    "critical_issues": [f"Review error: {e}"],
                    "suggestions": [],
                    "summary": "Review failed due to an error, defaulting to pass",
                },
            }

    def _route_after_review(self, state: AgentState) -> Literal["retry", "next_step", "finalize"]:
        """
        条件路由: 根据审查结果决定下一步

        逻辑:
          1. 如果 status 是 failed → finalize（报告失败）
          2. 如果审查不通过 且 重试次数 < max → retry
          3. 如果审查通过 且 还有步骤 → next_step（继续下一步）
          4. 如果审查通过 且 全部完成 → finalize
        """
        if state.get("status") == "failed":
            return "finalize"

        review = state.get("review_result", {})
        steps = state["steps"]
        step_idx = state["current_step_index"]
        retry_count = state.get("retry_count", 0)
        max_retries = state.get("max_retries", self.settings.max_retries)

        if not review.get("passed", False):
            if retry_count < max_retries:
                logger.info(
                    f"Step {step_idx + 1} failed review, retrying ({retry_count + 1}/{max_retries})"
                )
                self._emit(
                    state,
                    "retry_started",
                    step_id=steps[step_idx]["id"],
                    retry=retry_count + 1,
                    max_retries=max_retries,
                    reason=review.get("summary", ""),
                )
                return "retry"

            # 超过最大重试，跳过当前步骤
            logger.warning(
                f"Step {step_idx + 1} failed after {max_retries} retries, moving to next step"
            )

        # 移动到下一步或结束
        next_idx = step_idx + 1
        if next_idx < len(steps):
            return "next_step"
        else:
            return "finalize"

    async def _finalize_node(self, state: AgentState) -> dict:
        """Finalize Node: 生成最终报告"""
        self._emit(state, "task_completed")

        report = self._generate_report(state)
        logger.info(f"Task {state['task_id']} completed")

        return {
            "status": "done",
            "final_report": report,
        }

    # ── 公共接口 ──────────────────────────────

    async def run(self, task_id: str, user_request: str, provider: str = "openai") -> dict:
        """
        执行完整的 Agent 流水线

        Args:
            task_id: 任务 ID
            user_request: 用户自然语言需求
            provider: LLM provider (openai/deepseek)

        Returns:
            最终的 AgentState 字典
        """
        self.workspace.create(task_id)

        initial_state = create_initial_state(
            task_id=task_id,
            user_request=user_request,
            provider=provider,
            max_retries=self.settings.max_retries,
        )
        initial_state["workspace_path"] = str(self.workspace._get_path(task_id))

        self._emit(initial_state, "task_started")

        # LangGraph config（用于 checkpoint）
        config = {"configurable": {"thread_id": task_id}}

        try:
            final_state = await self._graph.ainvoke(initial_state, config)
            return final_state
        except Exception as e:
            logger.exception(f"Orchestrator run failed for task {task_id}")
            self._emit(initial_state, "task_failed", error=str(e))
            return {
                **initial_state,
                "status": "failed",
                "error_message": str(e),
                "final_report": self._generate_error_report(initial_state, e),
            }

    # ── 辅助方法 ──────────────────────────────

    def _emit(self, state: AgentState, event_type: str, **extra: dict) -> None:
        """发布事件到 EventBus"""
        event = WSEvent.create(
            event_type,
            task_id=state.get("task_id", "unknown"),
            **extra,
        )
        self.event_bus.publish(event)

    def _generate_report(self, state: AgentState) -> str:
        """生成最终开发报告"""
        steps = state["steps"]
        review = state.get("review_result", {})

        lines = [
            "# Development Report",
            "",
            f"## Task Summary",
            f"{state.get('plan_summary', 'N/A')}",
            "",
            f"## Result",
            f"- **Status**: {'PASSED' if review.get('passed', False) else 'COMPLETED WITH ISSUES'}",
            f"- **Review Score**: {review.get('overall_score', 0)}/100",
            "",
            "## Steps Executed",
        ]

        for i, step in enumerate(steps):
            status = "✅" if i < state["current_step_index"] else "⏳"
            lines.append(f"{status} **Step {step['id']}**: {step['description']}")

        lines.extend([
            "",
            "## Files Created",
            *[f"- `{f}`" for f in state.get("files_created", []) or ["(none)"]],
            "",
            "## Files Modified",
            *[f"- `{f}`" for f in state.get("files_modified", []) or ["(none)"]],
            "",
            "## Review Notes",
            review.get("summary", "No review available"),
        ])

        if review.get("suggestions"):
            lines.extend([
                "",
                "## Suggestions",
                *[f"- {s}" for s in review["suggestions"]],
            ])

        return "\n".join(lines)

    def _generate_error_report(self, state: AgentState, error: Exception) -> str:
        """生成错误报告"""
        return "\n".join([
            "# Development Report — FAILED",
            "",
            f"## Error",
            f"```",
            f"{type(error).__name__}: {error}",
            f"```",
            "",
            "The task could not be completed due to an unexpected error.",
            "Please check the logs and try again.",
        ])
