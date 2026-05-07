from __future__ import annotations

from .schemas import ChatRequest
from .config import GatewayConfig


def resolve_primary_model(request: ChatRequest, config: GatewayConfig) -> str:
    """
    根据请求类型选择主模型
    """

    if request.resolved_model:
        return request.resolved_model

    if (
        request.image_bytes or request.audio_bytes or request.video_bytes
    ) and config.model.vlm_model:
        request.resolved_model = config.model.vlm_model
        return request.resolved_model

    request.resolved_model = config.model.llm_model
    return request.resolved_model


def resolve_fallback_model(request: ChatRequest, config: GatewayConfig) -> str | None:
    """
    根据请求类型选择fallback模型
    """

    if request.image_bytes or request.audio_bytes or request.video_bytes:
        return config.model.fallback_vlm_model

    return config.model.fallback_llm_model
