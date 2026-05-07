from __future__ import annotations

import os
from pathlib import Path
from dotenv import load_dotenv

from .config import (
    GatewayConfig,
    TransportConfig,
    ModelConfig,
    RetryConfig,
    GovernanceConfig,
)


def _to_int(v, default):
    try:
        return int(v) if v not in (None, "") else default
    except Exception:
        return default


def _to_float(v, default):
    try:
        return float(v) if v not in (None, "") else default
    except Exception:
        return default


def _to_bool(v, default):
    if v in (None, ""):
        return default
    return str(v).strip().lower() in ("1", "true", "yes", "on")


def load_gateway_config(
    env_file: str | Path | None = None, **overrides
) -> GatewayConfig:
    if env_file:
        load_dotenv(env_file, override=False)
    else:
        load_dotenv(override=False)

    provider = overrides.get("provider") or os.getenv("LLM_PROVIDER", "openai")

    api_base = overrides.get("api_base") or os.getenv(
        "LLM_API_BASE",
        "https://api.openai.com/v1/chat/completions",
    )
    api_key = overrides.get("api_key") or os.getenv("LLM_API_KEY", "")
    timeout = _to_int(overrides.get("timeout") or os.getenv("LLM_TIMEOUT"), 120)

    max_retries = _to_int(
        overrides.get("max_retries") or os.getenv("LLM_MAX_RETRIES"), 3
    )
    base_delay = _to_float(
        overrides.get("base_delay") or os.getenv("LLM_RETRY_BASE_DELAY"), 1.0
    )
    max_delay = _to_float(
        overrides.get("max_delay") or os.getenv("LLM_RETRY_MAX_DELAY"), 8.0
    )
    jitter = _to_float(overrides.get("jitter") or os.getenv("LLM_RETRY_JITTER"), 0.5)

    llm_model = overrides.get("llm_model") or os.getenv("LLM_MODEL", "")
    vlm_model = overrides.get("vlm_model") or os.getenv("VLM_MODEL", "")

    fallback_llm_model = overrides.get("fallback_llm_model") or os.getenv(
        "FALLBACK_LLM_MODEL", ""
    )
    fallback_vlm_model = overrides.get("fallback_vlm_model") or os.getenv(
        "FALLBACK_VLM_MODEL", ""
    )

    temperature = _to_float(
        overrides.get("temperature") or os.getenv("LLM_TEMPERATURE"), 0.7
    )
    top_p = _to_float(overrides.get("top_p") or os.getenv("LLM_TOP_P"), 0.95)

    global_system_prompt = overrides.get("global_system_prompt") or os.getenv(
        "LLM_GLOBAL_SYSTEM_PROMPT",
        "你是企业内部AI助手。",
    )

    enable_fallback = _to_bool(
        overrides.get("enable_fallback") or os.getenv("LLM_ENABLE_FALLBACK"),
        True,
    )

    image_max_mb = _to_int(
        overrides.get("image_max_mb") or os.getenv("LLM_IMAGE_MAX_MB"), 5
    )
    audio_max_mb = _to_int(
        overrides.get("audio_max_mb") or os.getenv("LLM_AUDIO_MAX_MB"), 20
    )
    video_max_mb = _to_int(
        overrides.get("video_max_mb") or os.getenv("LLM_VIDEO_MAX_MB"), 50
    )

    return GatewayConfig(
        transport=TransportConfig(
            api_base=api_base,
            api_key=api_key,
            timeout=timeout,
            retry=RetryConfig(
                max_retries=max_retries,
                base_delay=base_delay,
                max_delay=max_delay,
                jitter=jitter,
            ),
        ),
        model=ModelConfig(
            provider=provider,
            llm_model=llm_model,
            vlm_model=vlm_model or None,
            fallback_llm_model=fallback_llm_model or None,
            fallback_vlm_model=fallback_vlm_model or None,
            temperature=temperature,
            top_p=top_p,
            global_system_prompt=global_system_prompt,
        ),
        governance=GovernanceConfig(
            enable_fallback=enable_fallback,
            image_max_mb=image_max_mb,
            audio_max_mb=audio_max_mb,
            video_max_mb=video_max_mb,
        ),
    )
