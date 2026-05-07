from __future__ import annotations

from typing import Optional, Dict, Any
from pydantic import BaseModel, ConfigDict, Field


class ChatRequest(BaseModel):
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        extra="ignore",
    )

    prompt: str
    system_prompt: Optional[str] = None

    temperature: Optional[float] = None
    top_p: Optional[float] = None

    json_mode: bool = False
    enable_thinking: Optional[bool] = None

    image_bytes: Optional[bytes] = None
    audio_bytes: Optional[bytes] = None
    video_bytes: Optional[bytes] = None

    resolved_model: Optional[str] = Field(default=None, exclude=True)
    fallback_used: bool = Field(default=False, exclude=True)


class ChatResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    raw: Dict[str, Any]

    @property
    def content(self) -> str:
        return (
            (self.raw.get("choices") or [{}])[0].get("message", {}).get("content", "")
        )


class StreamChunk(BaseModel):
    model_config = ConfigDict(extra="ignore")

    raw: Dict[str, Any]

    @property
    def content(self) -> str:
        choices = self.raw.get("choices") or [{}]
        delta = choices[0].get("delta", {})
        return delta.get("content", "")
