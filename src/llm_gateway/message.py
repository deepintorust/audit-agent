from typing import List
from .schemas import (
    ChatMessage,
    TextPart,
    ImagePart,
    ImageUrl,
    AudioPart,
    AudioInput,
    VideoPart,
    VideoUrl,
)


class MessageBuilder:
    @staticmethod
    def text(role: str, content: str) -> ChatMessage:
        return ChatMessage(role=role, content=content)

    @staticmethod
    def multimodal(text=None, image=None, audio=None, video=None) -> ChatMessage:
        parts: List = []
        if text:
            parts.append(TextPart(text=text))
        if image:
            parts.append(ImagePart(image_url=ImageUrl(url=image)))
        if audio:
            parts.append(AudioPart(input_audio=AudioInput(data=audio)))
        if video:
            parts.append(VideoPart(video_url=VideoUrl(url=video)))
        return ChatMessage(role="user", content=parts)

    @staticmethod
    def history_safe_message(
        text=None,
        has_image=False,
        has_audio=False,
        has_video=False,
        image_mime="image/jpeg",
        audio_mime="audio/wav",
        video_mime="video/mp4",
    ):
        desc = []
        if text:
            desc.append(text)
        if has_image:
            desc.append(f"[用户上传了一张图片: {image_mime}]")
        if has_audio:
            desc.append(f"[用户上传了一段音频: {audio_mime}]")
        if has_video:
            desc.append(f"[用户上传了一段视频: {video_mime}]")
        final_text = "\n".join(desc) if desc else "[用户发送了一条多模态消息]"
        return ChatMessage(role="user", content=final_text)
