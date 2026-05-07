from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class RetryConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")

    max_retries: int = Field(default=3)
    base_delay: float = Field(default=1.0)
    max_delay: float = Field(default=8.0)
    jitter: float = Field(default=0.5)


class TransportConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")

    api_base: str
    api_key: Optional[str] = None
    timeout: int = 120

    retry: RetryConfig = Field(default_factory=RetryConfig)


class ModelConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")

    provider: str = "openai"

    llm_model: str
    vlm_model: Optional[str] = None

    fallback_llm_model: Optional[str] = None
    fallback_vlm_model: Optional[str] = None

    temperature: float = 0.7
    top_p: float = 0.95

    global_system_prompt: Optional[str] = "你是企业内部AI助手。"


class GovernanceConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")

    enable_fallback: bool = True

    image_max_mb: int = 5
    audio_max_mb: int = 20
    video_max_mb: int = 50


class SessionConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")

    system_prompt: Optional[str] = None

    max_turns: int = 10
    token_budget: int = 6000


class GatewayConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")

    transport: TransportConfig
    model: ModelConfig
    governance: GovernanceConfig
