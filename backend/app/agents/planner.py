"""
Planner Agent — 需求分析 + 步骤拆解

职责:
  1. 理解用户的自然语言编程需求
  2. 推断合适的技术栈
  3. 拆分为 3-7 个有序执行步骤
  4. 输出结构化 JSON 计划

输出格式: Plan 模型（被 Orchestrator 解析后传给 Coder）
"""

import json
import logging

from langchain_core.language_models import BaseChatModel
from langchain_core.tools import BaseTool

from app.agents.base import AgentBase

logger = logging.getLogger(__name__)


PLANNER_SYSTEM_PROMPT = """You are a Senior Software Architect. Your job is to analyze a user's natural language programming request and produce a detailed, executable development plan.

## Your Task

1. Understand the user's requirement deeply
2. Determine the appropriate tech stack
3. Break the requirement into 3-7 ordered, independent steps
4. Output a structured JSON plan

## Rules

- Each step must produce concrete files
- Steps must be ordered by dependency (step 1 creates the skeleton, later steps add features)
- Each step should be independently verifiable
- Estimate complexity from 1 (trivial) to 5 (complex)
- Be practical, not over-engineered

## Output Format (STRICT JSON - no markdown, no explanation outside the JSON)

{
  "task_summary": "One-sentence summary of what will be built",
  "tech_stack": {
    "language": "python",
    "framework": "flask",
    "additional_dependencies": ["requests", "pytest"]
  },
  "steps": [
    {
      "id": 1,
      "description": "Create project skeleton with main entry point and dependency file",
      "files_to_create": ["main.py", "requirements.txt"],
      "files_to_modify": [],
      "expected_output": "Runnable project that starts without error",
      "complexity": 2,
      "depends_on": []
    },
    {
      "id": 2,
      "description": "Implement the core API endpoints",
      "files_to_create": ["api.py"],
      "files_to_modify": ["main.py"],
      "expected_output": "API endpoints return correct responses",
      "complexity": 3,
      "depends_on": [1]
    }
  ],
  "estimated_total_time": "3-5 minutes"
}

## Important
- Output ONLY the JSON object, nothing else.
- Do NOT wrap in markdown code blocks.
- Ensure the JSON is valid and parseable."""


class PlannerAgent(AgentBase):
    """需求规划 Agent — 将自然语言转为结构化开发计划"""

    name: str = "planner"

    def __init__(self, llm, tools=None, verbose=False):
        super().__init__(llm=llm, tools=tools, verbose=verbose)

    @property
    def system_prompt(self) -> str:
        return PLANNER_SYSTEM_PROMPT

    def plan(self, user_request: str) -> dict:
        """
        分析需求并返回结构化计划

        Args:
            user_request: 用户的自然语言需求

        Returns:
            dict: 包含 task_summary, tech_stack, steps 的计划

        Raises:
            ValueError: LLM 返回的 JSON 无法解析
        """
        logger.info(f"[Planner] Planning for: {user_request[:80]}...")

        raw_response = self.invoke(user_request)

        # 清理 LLM 输出（可能带 markdown 代码块标记）
        plan_json = _extract_json(raw_response)

        try:
            plan = json.loads(plan_json)
        except json.JSONDecodeError as e:
            logger.error(f"[Planner] Failed to parse JSON: {e}")
            logger.debug(f"[Planner] Raw response: {raw_response}")
            raise ValueError(
                f"Planner returned invalid JSON. Raw output: {raw_response[:300]}"
            ) from e

        # 校验必要字段
        required_fields = ["task_summary", "steps"]
        for field in required_fields:
            if field not in plan:
                raise ValueError(f"Planner plan missing required field: '{field}'")

        if not isinstance(plan["steps"], list) or len(plan["steps"]) == 0:
            raise ValueError("Planner plan must contain at least one step")

        # 补全可选字段
        plan.setdefault("tech_stack", {})
        plan.setdefault("estimated_total_time", "unknown")

        for step in plan["steps"]:
            step.setdefault("files_to_create", [])
            step.setdefault("files_to_modify", [])
            step.setdefault("expected_output", "")
            step.setdefault("complexity", 3)
            step.setdefault("depends_on", [])

        logger.info(
            f"[Planner] Plan created: {plan['task_summary'][:60]}... "
            f"({len(plan['steps'])} steps, tech={plan.get('tech_stack', {}).get('language', '?')})"
        )
        return plan


def _extract_json(text: str) -> str:
    """
    从 LLM 输出中提取 JSON

    处理常见情况:
      - 纯 JSON
      - ```json ... ```
      - ``` ... ```
      - 前后有说明文字
    """
    text = text.strip()

    # 移除 markdown 代码块
    if text.startswith("```"):
        lines = text.split("\n")
        # 找到 ``` 的结束位置
        end_idx = None
        for i in range(1, len(lines)):
            if lines[i].strip().startswith("```"):
                end_idx = i
                break
        if end_idx:
            text = "\n".join(lines[1:end_idx])
        else:
            text = "\n".join(lines[1:])

    # 查找 JSON 的起止位置
    start = text.find("{")
    end = text.rfind("}")

    if start != -1 and end != -1 and end > start:
        text = text[start : end + 1]

    return text.strip()
