"""
Agent 基类 — 所有 Agent 的公共抽象

提供:
  1. LLM 初始化（从 core.llm 工厂获取）
  2. Tool 绑定（从 ToolRegistry 获取）
  3. 统一 invoke 接口
  4. 异常处理和日志

设计理念:
  Agent = LLM + Tools + System Prompt
  每个子类只需定义 system_prompt 和调用方式。
"""

import logging
from abc import ABC, abstractmethod
from typing import Optional

from langchain_core.language_models import BaseChatModel
from langchain_core.tools import BaseTool

from app.config import get_settings

logger = logging.getLogger(__name__)


class AgentBase(ABC):
    """
    Agent 抽象基类

    子类必须实现:
      - name: Agent 标识名
      - system_prompt: 系统提示词
      - _run_impl(): 核心执行逻辑

    使用示例:
        agent = PlannerAgent(llm=my_llm, tools=[...])
        result = agent.invoke({"task": "创建天气API"})
    """

    name: str = "base"

    def __init__(
        self,
        llm: BaseChatModel,
        tools: Optional[list[BaseTool]] = None,
        verbose: bool = False,
    ):
        self.llm = llm
        self.tools = tools or []
        self.verbose = verbose or get_settings().debug
        self._bind_tools()

    def _bind_tools(self) -> None:
        """将 Tool 绑定到 LLM（LangChain Tool Calling）"""
        if self.tools:
            self.llm_with_tools = self.llm.bind_tools(self.tools)
        else:
            self.llm_with_tools = self.llm

    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """子类定义 Agent 的系统提示词"""
        ...

    def _build_messages(self, user_message: str) -> list:
        """构建发送给 LLM 的消息列表"""
        from langchain_core.messages import SystemMessage, HumanMessage

        return [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=user_message),
        ]

    def invoke(self, user_message: str) -> str:
        """
        调用 Agent（无 Tool 的标准对话模式）

        Args:
            user_message: 用户/上游 Agent 的输入

        Returns:
            LLM 的文本响应
        """
        logger.info(f"[{self.name}] Invoking with message ({len(user_message)} chars)")

        try:
            messages = self._build_messages(user_message)
            response = self.llm.invoke(messages)
            content = response.content if hasattr(response, "content") else str(response)

            if self.verbose:
                logger.debug(f"[{self.name}] Response: {content[:200]}...")

            return content

        except Exception as e:
            logger.exception(f"[{self.name}] Invocation failed")
            return f"ERROR [{self.name}]: {type(e).__name__}: {e}"

    def invoke_with_tools(self, user_message: str) -> str:
        """
        调用 Agent（带 Tool Calling）

        LangChain Tool Calling 流程:
          1. LLM 分析输入，决定是否调用 Tool
          2. 如果需要: 返回 tool_call → 执行 Tool → 将结果发回 LLM
          3. LLM 基于 Tool 结果生成最终回复
        """
        logger.info(f"[{self.name}] Invoking with tools ({len(self.tools)} tools)")

        if not self.tools:
            logger.warning(f"[{self.name}] No tools bound, falling back to standard invoke")
            return self.invoke(user_message)

        try:
            messages = self._build_messages(user_message)
            response = self.llm_with_tools.invoke(messages)

            # 如果 LLM 决定调用 Tool
            if hasattr(response, "tool_calls") and response.tool_calls:
                from langchain_core.messages import ToolMessage

                # 执行所有 tool calls
                for tool_call in response.tool_calls:
                    tool_name = tool_call.get("name", "unknown")
                    tool_args = tool_call.get("args", {})
                    logger.info(f"[{self.name}] Tool call: {tool_name}({tool_args})")

                    # 查找并执行 Tool
                    tool = self._find_tool(tool_name)
                    if tool:
                        tool_result = tool.invoke(tool_args)
                        messages.append(
                            ToolMessage(
                                content=str(tool_result),
                                tool_call_id=tool_call["id"],
                            )
                        )
                    else:
                        messages.append(
                            ToolMessage(
                                content=f"Tool '{tool_name}' not found",
                                tool_call_id=tool_call["id"],
                            )
                        )

                # 将 Tool 结果发回 LLM 获取最终回复
                final_response = self.llm_with_tools.invoke(messages)
                content = (
                    final_response.content
                    if hasattr(final_response, "content")
                    else str(final_response)
                )
                return content

            # LLM 不需要调用 Tool，直接返回
            content = response.content if hasattr(response, "content") else str(response)
            return content

        except Exception as e:
            logger.exception(f"[{self.name}] Tool invocation failed")
            return f"ERROR [{self.name}]: {type(e).__name__}: {e}"

    def _find_tool(self, name: str) -> Optional[BaseTool]:
        """按名称查找已绑定的 Tool"""
        for tool in self.tools:
            if tool.name == name:
                return tool
        return None

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.name} tools={len(self.tools)}>"
