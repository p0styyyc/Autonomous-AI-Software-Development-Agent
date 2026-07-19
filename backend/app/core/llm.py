"""
LLM 工厂模块 — 统一创建不同 Provider 的模型实例

设计模式: 工厂模式 (Factory Pattern)
职责:
  1. 根据配置自动选择 Provider (OpenAI / DeepSeek)
  2. 统一模型参数（temperature, max_tokens 等）
  3. 对外屏蔽不同 SDK 的差异

使用示例:
    from app.core.llm import create_llm, LLMProvider

    llm = create_llm(LLMProvider.OPENAI)  # 使用默认模型
    llm = create_llm(LLMProvider.DEEPSEEK, model="deepseek-coder")
"""

from enum import Enum
from typing import Optional

from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI

from app.config import get_settings


class LLMProvider(str, Enum):
    """支持的 LLM Provider 枚举"""
    OPENAI = "openai"
    DEEPSEEK = "deepseek"


# Provider 默认模型映射
_DEFAULT_MODELS: dict[LLMProvider, str] = {
    LLMProvider.OPENAI: "gpt-4o-mini",
    LLMProvider.DEEPSEEK: "deepseek-chat",
}

# Coder 专用模型（更强的代码能力）
_CODER_MODELS: dict[LLMProvider, str] = {
    LLMProvider.OPENAI: "gpt-4o",
    LLMProvider.DEEPSEEK: "deepseek-coder",
}


def _build_openai(model: str, temperature: float, max_tokens: int) -> ChatOpenAI:
    """构建 OpenAI 模型实例"""
    settings = get_settings()
    if not settings.openai_api_key:
        raise ValueError("OPENAI_API_KEY 未配置，请在 .env 中设置")
    return ChatOpenAI(
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        api_key=settings.openai_api_key,
    )


def _build_deepseek(model: str, temperature: float, max_tokens: int) -> ChatOpenAI:
    """
    构建 DeepSeek 模型实例

    DeepSeek API 兼容 OpenAI SDK 格式，
    只需修改 base_url 和 api_key 即可复用 ChatOpenAI
    """
    settings = get_settings()
    if not settings.deepseek_api_key:
        raise ValueError("DEEPSEEK_API_KEY 未配置，请在 .env 中设置")
    return ChatOpenAI(
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        api_key=settings.deepseek_api_key,
        base_url="https://api.deepseek.com/v1",
    )


# Provider → 构建函数的映射
_BUILDERS = {
    LLMProvider.OPENAI: _build_openai,
    LLMProvider.DEEPSEEK: _build_deepseek,
}


def create_llm(
    provider: Optional[LLMProvider] = None,
    model: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    *,
    coder_mode: bool = False,
) -> BaseChatModel:
    """
    LLM 工厂函数 — 创建并返回 LangChain BaseChatModel 实例

    Args:
        provider: LLM Provider，默认从配置读取
        model: 模型名称，默认使用 provider 的默认模型
        temperature: 温度参数 (0.0-2.0)，默认从配置读取
        max_tokens: 最大输出 token 数
        coder_mode: 是否使用代码生成专用模型（更强但更贵）

    Returns:
        BaseChatModel 实例

    Raises:
        ValueError: API Key 未配置或不支持的 Provider
    """
    settings = get_settings()

    # 解析 Provider
    if provider is None:
        provider = LLMProvider(settings.default_provider)

    # 解析模型名
    if model is None:
        if coder_mode:
            model = _CODER_MODELS.get(provider, _DEFAULT_MODELS[provider])
        else:
            model = _DEFAULT_MODELS.get(provider, settings.default_model)

    # 解析参数
    temperature = temperature if temperature is not None else settings.llm_temperature
    max_tokens = max_tokens if max_tokens is not None else settings.llm_max_tokens

    # 调用对应的构建函数
    builder = _BUILDERS.get(provider)
    if builder is None:
        raise ValueError(f"不支持的 LLM Provider: {provider}")

    return builder(model=model, temperature=temperature, max_tokens=max_tokens)


def create_coder_llm(provider: Optional[LLMProvider] = None) -> BaseChatModel:
    """快捷方法：创建代码生成专用 LLM（使用更强的模型）"""
    return create_llm(provider=provider, coder_mode=True, temperature=0.0)


def create_planner_llm(provider: Optional[LLMProvider] = None) -> BaseChatModel:
    """快捷方法：创建规划专用 LLM（需要创造性但可控）"""
    return create_llm(provider=provider, temperature=0.3)


def create_reviewer_llm(provider: Optional[LLMProvider] = None) -> BaseChatModel:
    """快捷方法：创建审查专用 LLM（需要精确和挑剔）"""
    return create_llm(provider=provider, temperature=0.0)
