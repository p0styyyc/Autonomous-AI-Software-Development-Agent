"""
Coding Agent — 代码生成与文件操作

职责:
  1. 接收单个 Step + 项目现状
  2. 使用 Tool Calling 创建/修改文件
  3. 生成高质量、可运行的代码

工作模式:
  有 Tool: LLM 自主决定何时调用 FileCreate/Read/Modify
  无 Tool: 直接生成代码文本（测试用）
"""

import logging

from langchain_core.language_models import BaseChatModel
from langchain_core.tools import BaseTool

from app.agents.base import AgentBase

logger = logging.getLogger(__name__)


CODER_SYSTEM_PROMPT = """You are a Senior Software Engineer. Your job is to implement code based on a specific development step.

## Your Task

You will receive:
1. A task description (what to build)
2. The current step details (what files to create/modify)
3. The existing project files (if any)

Use the available tools to create and modify files as specified in the step.

## Code Quality Standards

1. **Type Annotations**: Use type hints in Python (def func(x: str) -> int:)
2. **Docstrings**: Every function/class has a brief docstring
3. **Error Handling**: External calls (API, file I/O) wrapped in try/except
4. **Logging**: Use `logging` module, not `print()`
5. **No Secrets**: Never hardcode API keys, use `os.environ.get()` or similar
6. **PEP 8**: Follow Python style conventions
7. **Testable**: Code should be structured for easy testing

## Before Writing Code

1. Use `file_read` to check any existing files you need to modify
2. Then use `file_create` for new files or `file_modify` for existing ones

## Output

After creating/modifying files, briefly summarize:
- What files were created/modified
- Any important design decisions
- How to verify the output works
"""


class CodingAgent(AgentBase):
    """代码生成 Agent — 根据计划步骤编写代码"""

    name: str = "coder"

    def __init__(self, llm, tools=None, verbose=False):
        super().__init__(llm=llm, tools=tools, verbose=verbose)

    @property
    def system_prompt(self) -> str:
        return CODER_SYSTEM_PROMPT

    def implement_step(self, task_summary: str, step: dict, workspace_state: str) -> str:
        """
        实现单个开发步骤

        Args:
            task_summary: 项目整体概述
            step: 当前步骤详情 (来自 Planner 的 plan)
            workspace_state: 工作区当前文件树/内容摘要

        Returns:
            LLM 的代码生成结果（含 Tool Calling 执行记录）
        """
        prompt = f"""## Project Goal
{task_summary}

## Current Step (ID: {step.get('id', '?')})
{step.get('description', 'No description')}

**Files to Create:** {', '.join(step.get('files_to_create', [])) or 'None'}
**Files to Modify:** {', '.join(step.get('files_to_modify', [])) or 'None'}
**Expected Output:** {step.get('expected_output', 'Not specified')}

## Current Workspace State
{workspace_state or '(empty workspace — no files exist yet)'}

## Instructions
1. First, read any files you need to modify using file_read
2. Then create or modify files as specified above
3. Make sure all code follows the quality standards
4. After done, summarize what you did
"""

        logger.info(
            f"[Coder] Implementing step {step.get('id')}: "
            f"create={step.get('files_to_create')}, modify={step.get('files_to_modify')}"
        )

        if self.tools:
            return self.invoke_with_tools(prompt)
        else:
            return self.invoke(prompt)
