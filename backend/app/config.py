"""
Autonomous AI Software Development Agent — 配置管理

使用 pydantic-settings 实现类型安全的配置加载。
支持 .env 文件和环境变量，优先级: 环境变量 > .env > 默认值
"""

from pathlib import Path
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用全局配置，自动从 .env 和环境变量加载"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── LLM ─────────────────────────────────────────────
    openai_api_key: str = Field(default="", description="OpenAI API Key")
    deepseek_api_key: str = Field(default="", description="DeepSeek API Key")
    default_provider: str = Field(default="openai", description="默认 LLM Provider")
    default_model: str = Field(default="gpt-4o-mini", description="默认模型")
    llm_temperature: float = Field(default=0.1, ge=0.0, le=2.0)
    llm_max_tokens: int = Field(default=4096, ge=1, le=128000)

    # ── 服务 ───────────────────────────────────────────
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000, ge=1, le=65535)
    debug: bool = Field(default=False)
    log_level: str = Field(default="INFO")

    # ── 工作区 ─────────────────────────────────────────
    workspace_base_dir: str = Field(default="./workspace")
    max_workspace_size_mb: int = Field(default=100, ge=1)

    # ── Docker 沙箱 ────────────────────────────────────
    sandbox_image: str = Field(default="python:3.11-slim")
    sandbox_memory_limit: str = Field(default="512m")
    sandbox_cpu_limit: float = Field(default=1.0)
    sandbox_timeout_seconds: int = Field(default=30, ge=1, le=300)
    sandbox_network_disabled: bool = Field(default=True)

    # ── Agent ──────────────────────────────────────────
    max_retries: int = Field(default=3, ge=0, le=10)
    max_steps: int = Field(default=7, ge=1, le=20)

    # ── Redis ──────────────────────────────────────────
    redis_url: str = Field(default="redis://localhost:6379/0")

    @property
    def workspace_path(self) -> Path:
        """工作区根目录的绝对路径"""
        path = Path(self.workspace_base_dir).resolve()
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def is_llm_configured(self) -> bool:
        """检查是否至少配置了一个 LLM Provider"""
        return bool(self.openai_api_key or self.deepseek_api_key)


@lru_cache
def get_settings() -> Settings:
    """获取配置单例（带缓存，避免重复解析 .env）"""
    return Settings()
