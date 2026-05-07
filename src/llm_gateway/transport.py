from __future__ import annotations

import json
import httpx
from typing import AsyncGenerator

from .config import GatewayConfig
from .schemas import ChatResponse, StreamChunk
from .exceptions import TransportError
from .retry import run_with_retry


class AsyncTransport:
    def __init__(self, config: GatewayConfig):
        self.config = config

        headers = {
            "Content-Type": "application/json",
        }

        if config.transport.api_key:
            headers["Authorization"] = f"Bearer {config.transport.api_key}"

        limits = httpx.Limits(
            max_connections=100,
            max_keepalive_connections=20,
            keepalive_expiry=30,
        )

        self.client = httpx.AsyncClient(
            headers=headers,
            timeout=config.transport.timeout,
            limits=limits,
        )

    async def aclose(self):
        try:
            await self.client.aclose()
        except Exception:
            pass

    async def _do_post(self, payload: dict) -> ChatResponse:
        try:
            resp = await self.client.post(
                self.config.transport.api_base,
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
            return ChatResponse(raw=data)

        except Exception as exc:
            raise TransportError(str(exc))

    async def post(self, payload: dict) -> ChatResponse:
        return await run_with_retry(
            self._do_post,
            self.config.transport.retry,
            payload,
        )

    async def _do_stream_post(self, payload: dict) -> AsyncGenerator[StreamChunk, None]:
        payload["stream"] = True

        try:
            async with self.client.stream(
                "POST",
                self.config.transport.api_base,
                json=payload,
            ) as resp:
                resp.raise_for_status()

                async for line in resp.aiter_lines():
                    if not line:
                        continue

                    if line.startswith("data: "):
                        line = line[6:]

                    if line.strip() == "[DONE]":
                        break

                    try:
                        data = json.loads(line)
                        yield StreamChunk(raw=data)
                    except Exception:
                        continue

        except Exception as exc:
            raise TransportError(str(exc))

    async def stream_post(self, payload: dict) -> AsyncGenerator[StreamChunk, None]:
        """
        stream场景不能直接套普通retry函数，
        因为generator需要重新建立连接，所以单独做一层。
        """
        last_exc = None

        for attempt in range(self.config.transport.retry.max_retries):
            try:
                async for chunk in self._do_stream_post(payload):
                    yield chunk
                return

            except Exception as exc:
                last_exc = exc

                if attempt >= self.config.transport.retry.max_retries - 1:
                    break

        raise TransportError(str(last_exc))
