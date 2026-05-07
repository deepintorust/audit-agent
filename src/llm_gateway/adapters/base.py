from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class ProviderAdapter(ABC):
    @abstractmethod
    def build_text_part(self, text: str) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def build_image_part(self, image_data_uri: str) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def build_audio_part(self, audio_b64: str) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def build_video_part(self, video_data_uri: str) -> Dict[str, Any]:
        raise NotImplementedError

    def build_user_content(
        self,
        prompt: str,
        image_data_uri: Optional[str] = None,
        audio_b64: Optional[str] = None,
        video_data_uri: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        content: List[Dict[str, Any]] = [self.build_text_part(prompt)]

        if image_data_uri:
            content.append(self.build_image_part(image_data_uri))

        if audio_b64:
            content.append(self.build_audio_part(audio_b64))

        if video_data_uri:
            content.append(self.build_video_part(video_data_uri))

        return content
