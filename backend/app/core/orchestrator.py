"""
LangGraph Orchestrator — 多 Agent 流水线编排器

核心流程:
    START → planner → [failed? → finalize]
                   ↓
                 coder → [done? → finalize]
                   ↓
               executor
                   ↓
               reviewer → [retry → coder] [next → coder] [done → finalize]
"""

import logging
from typing import Literal

from langgraph.graph import END, StateGraph
from langgraph.checkpoint.memory import MemorySaver

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
    """Agent 流水线编排器 — LangGraph StateGraph 管理 4 个 Agent"""

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

        workflow.add_node("planner", self._planner_node)
        workflow.add_node("coder", self._coder_node)
        workflow.add_node("executor", self._executor_node)
        workflow.add_node("reviewer", self._reviewer_node)
        workflow.add_node("finalize", self._finalize_node)

        workflow.set_entry_point("planner")

        # Planner → 成功进 coder，失败进 finalize
        workflow.add_conditional_edges(
            "planner",
            self._route_after_planner,
            {"coder": "coder", "finalize": "finalize"},
        )

        # Coder → 成功进 executor，失败/done 进 finalize
        workflow.add_conditional_edges(
            "coder",
            self._route_after_coder,
            {"executor": "executor", "finalize": "finalize"},
        )

        # Executor → Reviewer
        workflow.add_edge("executor", "reviewer")

        # Reviewer → retry / next_step / finalize
        workflow.add_conditional_edges(
            "reviewer",
            self._route_after_review,
            {"retry": "coder", "next_step": "coder", "finalize": "finalize"},
        )

        workflow.add_edge("finalize", END)

        return workflow.compile(checkpointer=MemorySaver())

    # ── Routing ────────────────────────────────

    def _route_after_planner(self, state: AgentState) -> Literal["coder", "finalize"]:
        if state.get("status") == "failed":
            return "finalize"
        return "coder"

    def _route_after_coder(self, state: AgentState) -> Literal["executor", "finalize"]:
        status = state.get("status", "")
        if status in ("failed", "done"):
            return "finalize"
        return "executor"

    def _route_after_review(self, state: AgentState) -> Literal["retry", "next_step", "finalize"]:
        status = state.get("status", "")
        if status == "finalize":
            return "finalize"
        if status == "retry":
            return "retry"
        # status == "next_step" or "coding" (shouldn't happen normally)
        steps = state.get("steps", [])
        next_idx = state.get("current_step_index", 0)
        if next_idx >= len(steps):
            return "finalize"
        return "next_step"

    # ── Nodes ──────────────────────────────────

    async def _planner_node(self, state: AgentState) -> dict:
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
                "retry_count": 0,
                "status": "coding",
                "files_created": [],
                "files_modified": [],
            }
        except Exception as e:
            logger.exception("Planner node failed")
            self._emit(state, "task_failed", error=str(e))
            return {
                "status": "failed",
                "error_message": f"Planning failed: {e}",
            }

    async def _coder_node(self, state: AgentState) -> dict:
        steps = state.get("steps", [])
        step_idx = state.get("current_step_index", 0)

        # 所有步骤完成 或 步骤列表为空
        if step_idx >= len(steps) or len(steps) == 0:
            return {"status": "done"}

        step = steps[step_idx]

        self._emit(
            state,
            "step_started",
            step_id=step.get("id", step_idx + 1),
            description=step.get("description", ""),
            step_index=step_idx,
            total_steps=len(steps),
        )
        self._emit(state, "coding_started", step_id=step.get("id", step_idx + 1))

        try:
            llm = create_coder_llm()
            tool_registry = create_tool_registry(
                str(self.workspace._get_path(state["task_id"]))
            )
            coder = CodingAgent(llm=llm, tools=tool_registry.for_coder())

            workspace_summary = self.workspace.get_workspace_summary(state["task_id"])

            coder.implement_step(
                task_summary=state.get("plan_summary", ""),
                step=step,
                workspace_state=workspace_summary,
            )

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
                step_id=step.get("id", step_idx + 1),
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
                "status": "failed",
                "error_message": f"Coding failed: {e}",
            }

    async def _executor_node(self, state: AgentState) -> dict:
        self._emit(state, "executing_started")

        try:
            code_files = collect_workspace_files(
                str(self.workspace._get_path(state["task_id"]))
            )

            execution_data = {
                "exit_code": -1,
                "stdout": "",
                "stderr": "No files to execute",
                "execution_time_ms": 0,
                "timed_out": False,
            }

            if code_files:
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

            if execution_data["exit_code"] == 0:
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
                    "exit_code": -1, "stdout": "", "stderr": str(e),
                    "execution_time_ms": 0, "timed_out": False,
                },
                "status": "reviewing",
            }

    async def _reviewer_node(self, state: AgentState) -> dict:
        """Reviewer Node: 审查代码 + 决定下一步状态"""
        steps = state.get("steps", [])
        step_idx = state.get("current_step_index", 0)

        # 安全兜底：没有步骤时直接结束
        if len(steps) == 0 or step_idx >= len(steps):
            return {"status": "finalize"}

        step = steps[step_idx]
        self._emit(state, "reviewing_started", step_id=step.get("id", step_idx + 1))

        try:
            llm = create_reviewer_llm()
            reviewer = ReviewAgent(llm=llm)

            workspace_summary = self.workspace.get_workspace_summary(state["task_id"])

            exec_result = state.get("execution_result", {})
            exec_str = (
                f"Exit Code: {exec_result.get('exit_code', '?')}\n"
                f"Stdout: {exec_result.get('stdout', '')[:1000]}\n"
                f"Stderr: {exec_result.get('stderr', '')[:1000]}\n"
                f"Timed Out: {exec_result.get('timed_out', False)}"
            )

            review = reviewer.review(
                step_description=step.get("description", ""),
                expected_output=step.get("expected_output", ""),
                code=workspace_summary[:8000],
                execution_result=exec_str,
            )

            review_data = {
                "passed": review.get("passed", False),
                "overall_score": review.get("overall_score", 0),
                "dimensions": review.get("dimensions", {}),
                "critical_issues": review.get("critical_issues", []),
                "suggestions": review.get("suggestions", []),
                "summary": review.get("summary", ""),
            }

            if review_data["passed"]:
                self._emit(state, "review_pass", **review_data)
            else:
                self._emit(state, "review_fail", **review_data)

            # ── 状态转换（关键：在 node 中修改状态，而非路由函数中）──
            max_retries = state.get("max_retries", self.settings.max_retries)
            retry_count = state.get("retry_count", 0)

            if review_data["passed"]:
                # 通过 → 下一步
                next_idx = step_idx + 1
                new_retry = 0
                if next_idx >= len(steps):
                    return {
                        "review_result": review_data,
                        "current_step_index": next_idx,
                        "retry_count": 0,
                        "status": "finalize",
                    }
                else:
                    return {
                        "review_result": review_data,
                        "current_step_index": next_idx,
                        "retry_count": 0,
                        "status": "next_step",
                    }
            else:
                # 未通过
                new_retry = retry_count + 1
                if new_retry <= max_retries:
                    self._emit(
                        state,
                        "retry_started",
                        step_id=step.get("id", step_idx + 1),
                        retry=new_retry,
                        max_retries=max_retries,
                        reason=review_data.get("summary", ""),
                    )
                    return {
                        "review_result": review_data,
                        "retry_count": new_retry,
                        "status": "retry",
                    }
                else:
                    # 超过最大重试，跳过当前步骤
                    logger.warning(
                        f"Step {step_idx + 1} exceeded max retries ({max_retries}), skipping"
                    )
                    next_idx = step_idx + 1
                    if next_idx >= len(steps):
                        return {
                            "review_result": review_data,
                            "current_step_index": next_idx,
                            "retry_count": 0,
                            "status": "finalize",
                        }
                    else:
                        return {
                            "review_result": review_data,
                            "current_step_index": next_idx,
                            "retry_count": 0,
                            "status": "next_step",
                        }

        except Exception as e:
            logger.exception("Reviewer node failed")
            # 异常时跳过当前步骤，避免死循环
            next_idx = step_idx + 1
            if next_idx >= len(steps):
                return {"status": "finalize"}
            return {
                "current_step_index": next_idx,
                "retry_count": 0,
                "status": "next_step",
            }

    async def _finalize_node(self, state: AgentState) -> dict:
        self._emit(state, "task_completed")
        report = self._generate_report(state)
        logger.info(f"Task {state['task_id']} completed")
        return {"status": "done", "final_report": report}

    # ── Public API ─────────────────────────────

    async def run(self, task_id: str, user_request: str, provider: str = "openai") -> dict:
        self.workspace.create(task_id)

        initial_state = create_initial_state(
            task_id=task_id,
            user_request=user_request,
            provider=provider,
            max_retries=self.settings.max_retries,
        )
        initial_state["workspace_path"] = str(self.workspace._get_path(task_id))

        self._emit(initial_state, "task_started")

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

    # ── Helpers ────────────────────────────────

    def _emit(self, state: AgentState, event_type: str, **extra) -> None:
        self.event_bus.publish(WSEvent.create(
            event_type, task_id=state.get("task_id", "unknown"), **extra,
        ))

    def _generate_report(self, state: AgentState) -> str:
        steps = state.get("steps", [])
        review = state.get("review_result", {})
        lines = [
            "# Development Report", "",
            f"## Task Summary",
            f"{state.get('plan_summary', 'N/A')}", "",
            f"## Result",
            f"- **Status**: {'PASSED' if review.get('passed') else 'COMPLETED'}",
            f"- **Review Score**: {review.get('overall_score', 0)}/100", "",
            "## Steps Executed",
        ]
        done_idx = max(0, state.get("current_step_index", 0) - 1)
        for i, step in enumerate(steps):
            icon = "✅" if i <= done_idx else "⏳"
            lines.append(f"{icon} **Step {step.get('id', i+1)}**: {step.get('description', '')}")

        lines.extend([
            "", "## Files Created",
            *[f"- `{f}`" for f in state.get("files_created", []) or ["(none)"]],
            "", "## Files Modified",
            *[f"- `{f}`" for f in state.get("files_modified", []) or ["(none)"]],
            "", "## Review Notes",
            review.get("summary", "No review available"),
        ])
        if review.get("suggestions"):
            lines.extend(["", "## Suggestions", *[f"- {s}" for s in review["suggestions"]]])
        return "\n".join(lines)

    def _generate_error_report(self, state: AgentState, error: Exception) -> str:
        return "\n".join([
            "# Development Report — FAILED", "",
            f"## Error", f"```", f"{type(error).__name__}: {error}", f"```", "",
            "The task could not be completed due to an unexpected error.",
            "Please check the logs and try again.",
        ])
