from __future__ import annotations

from typing import AsyncGenerator, List, Dict, Any

from .config import GatewayConfig
from .schemas import ChatRequest
from .session import ChatSession
from .transport import AsyncTransport
from .router import resolve_primary_model, resolve_fallback_model
from .media import build_multimodal_user_content, validate_media_size
from .hooks import RequestTrace


class LLMGatewayClient:
    def __init__(self, config: GatewayConfig):
        self.config = config
        self.transport = AsyncTransport(config)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.aclose()

    async def aclose(self):
        await self.transport.aclose()

    # =========================================================
    # system prompt优先级
    # request > session > global
    # =========================================================
    def _resolve_system_prompt(
        self,
        request: ChatRequest,
        session: ChatSession | None = None,
    ) -> str | None:
        if request.system_prompt:
            return request.system_prompt

        if session and session.config.system_prompt:
            return session.config.system_prompt

        return self.config.model.global_system_prompt

    # =========================================================
    # 历史中不要保存真实base64媒体，避免history爆炸
    # =========================================================
    def _build_history_safe_user_text(self, request: ChatRequest) -> str:
        desc = [request.prompt]

        if request.image_bytes:
            desc.append("[用户上传了一张图片]")

        if request.audio_bytes:
            desc.append("[用户上传了一段音频]")

        if request.video_bytes:
            desc.append("[用户上传了一段视频]")

        return "\n".join(desc)

    # =========================================================
    # 组装messages
    # =========================================================
    def _build_messages(
        self,
        request: ChatRequest,
        session: ChatSession | None = None,
    ) -> List[Dict[str, Any]]:
        messages: List[Dict[str, Any]] = []

        system_prompt = self._resolve_system_prompt(request, session)
        if system_prompt:
            messages.append(
                {
                    "role": "system",
                    "content": system_prompt,
                }
            )

        if session:
            messages.extend(session.get_history())

        user_content = build_multimodal_user_content(
            provider=self.config.model.provider,
            prompt=request.prompt,
            image_bytes=request.image_bytes,
            audio_bytes=request.audio_bytes,
            video_bytes=request.video_bytes,
        )

        messages.append(
            {
                "role": "user",
                "content": user_content,
            }
        )

        return messages

    # =========================================================
    # payload构建
    # =========================================================
    def _build_payload(
        self,
        request: ChatRequest,
        session: ChatSession | None = None,
        stream: bool = False,
        force_model: str | None = None,
    ) -> dict:
        model_name = force_model or resolve_primary_model(request, self.config)

        payload = {
            "model": model_name,
            "messages": self._build_messages(request, session),
            "stream": stream,
            "temperature": (
                self.config.model.temperature
                if request.temperature is None
                else request.temperature
            ),
            "top_p": (
                self.config.model.top_p if request.top_p is None else request.top_p
            ),
        }

        if request.enable_thinking is not None:
            payload["chat_template_kwargs"] = {
                "enable_thinking": request.enable_thinking,
            }

        if request.json_mode:
            payload["response_format"] = {"type": "json_object"}

        return payload

    # =========================================================
    # session写回
    # =========================================================
    def _save_session_history(
        self,
        request: ChatRequest,
        answer: str,
        session: ChatSession,
    ):
        safe_user_text = self._build_history_safe_user_text(request)

        session.add_message(
            "user",
            safe_user_text,
        )
        session.add_message(
            "assistant",
            answer,
        )

    # =========================================================
    # 单轮chat
    # =========================================================
    async def chat(
        self,
        request: ChatRequest,
        session: ChatSession | None = None,
    ) -> str:
        trace = RequestTrace()

        validate_media_size(
            self.config,
            request.image_bytes,
            request.audio_bytes,
            request.video_bytes,
        )

        try:
            payload = self._build_payload(request, session, stream=False)
            result = await self.transport.post(payload)
            content = result.content

            if session:
                self._save_session_history(request, content, session)

            trace.success()
            return content

        except Exception as primary_exc:
            # ================= fallback =================
            if self.config.governance.enable_fallback:
                fallback_model = resolve_fallback_model(request, self.config)

                if fallback_model:
                    try:
                        payload = self._build_payload(
                            request,
                            session,
                            stream=False,
                            force_model=fallback_model,
                        )
                        result = await self.transport.post(payload)
                        content = result.content

                        if session:
                            self._save_session_history(request, content, session)

                        trace.success()
                        return content

                    except Exception:
                        pass

            trace.failed(primary_exc)
            raise

    # =========================================================
    # 流式chat
    # =========================================================
    async def stream_chat(
        self,
        request: ChatRequest,
        session: ChatSession | None = None,
    ) -> AsyncGenerator[str, None]:
        trace = RequestTrace()
        full_text = ""

        validate_media_size(
            self.config,
            request.image_bytes,
            request.audio_bytes,
            request.video_bytes,
        )

        try:
            payload = self._build_payload(request, session, stream=True)

            async for chunk in self.transport.stream_post(payload):
                text = chunk.content
                if text:
                    full_text += text
                    yield text

            if session:
                self._save_session_history(request, full_text, session)

            trace.success()

        except Exception as primary_exc:
            if self.config.governance.enable_fallback:
                fallback_model = resolve_fallback_model(request, self.config)

                if fallback_model:
                    try:
                        payload = self._build_payload(
                            request,
                            session,
                            stream=True,
                            force_model=fallback_model,
                        )

                        async for chunk in self.transport.stream_post(payload):
                            text = chunk.content
                            if text:
                                full_text += text
                                yield text

                        if session:
                            self._save_session_history(request, full_text, session)

                        trace.success()
                        return

                    except Exception:
                        pass

            trace.failed(primary_exc)
            raise
