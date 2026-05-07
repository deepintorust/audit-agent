from __future__ import annotations

import base64

from .adapters import OpenAIAdapter, SiliconFlowAdapter
from .exceptions import UnsupportedProviderError, PayloadBuildError
from .config import GatewayConfig


def to_data_uri(data: bytes, mime: str) -> str:
    b64 = base64.b64encode(data).decode("utf-8")
    return f"data:{mime};base64,{b64}"


def get_provider_adapter(provider: str):
    provider = (provider or "openai").lower()

    if provider == "openai":
        return OpenAIAdapter()

    if provider == "siliconflow":
        return SiliconFlowAdapter()

    raise UnsupportedProviderError(f"unsupported provider: {provider}")


def validate_media_size(
    config: GatewayConfig,
    image_bytes: bytes | None = None,
    audio_bytes: bytes | None = None,
    video_bytes: bytes | None = None,
):
    if image_bytes:
        size_mb = len(image_bytes) / 1024 / 1024
        if size_mb > config.governance.image_max_mb:
            raise PayloadBuildError(
                f"image too large: {size_mb:.2f}MB > {config.governance.image_max_mb}MB"
            )

    if audio_bytes:
        size_mb = len(audio_bytes) / 1024 / 1024
        if size_mb > config.governance.audio_max_mb:
            raise PayloadBuildError(
                f"audio too large: {size_mb:.2f}MB > {config.governance.audio_max_mb}MB"
            )

    if video_bytes:
        size_mb = len(video_bytes) / 1024 / 1024
        if size_mb > config.governance.video_max_mb:
            raise PayloadBuildError(
                f"video too large: {size_mb:.2f}MB > {config.governance.video_max_mb}MB"
            )


def build_multimodal_user_content(
    provider: str,
    prompt: str,
    image_bytes: bytes | None = None,
    audio_bytes: bytes | None = None,
    video_bytes: bytes | None = None,
):
    adapter = get_provider_adapter(provider)

    image_data_uri = None
    audio_b64 = None
    video_data_uri = None

    if image_bytes:
        image_data_uri = to_data_uri(image_bytes, "image/jpeg")

    if audio_bytes:
        audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")

    if video_bytes:
        video_data_uri = to_data_uri(video_bytes, "video/mp4")

    return adapter.build_user_content(
        prompt=prompt,
        image_data_uri=image_data_uri,
        audio_b64=audio_b64,
        video_data_uri=video_data_uri,
    )
