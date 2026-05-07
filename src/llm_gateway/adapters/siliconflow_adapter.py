from __future__ import annotations

from typing import Dict, Any
from .base import ProviderAdapter


class SiliconFlowAdapter(ProviderAdapter):
    def build_text_part(self, text: str) -> Dict[str, Any]:
        return {
            "type": "text",
            "text": text,
        }

    def build_image_part(self, image_data_uri: str) -> Dict[str, Any]:
        return {
            "type": "image_url",
            "image_url": image_data_uri,
        }

    def build_audio_part(self, audio_b64: str) -> Dict[str, Any]:
        return {
            "type": "input_audio",
            "input_audio": {
                "data": audio_b64,
                "format": "mp3",
            },
        }

    def build_video_part(self, video_data_uri: str) -> Dict[str, Any]:
        return {
            "type": "video_url",
            "video_url": video_data_uri,
        }
