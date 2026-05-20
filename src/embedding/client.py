# from __future__ import annotations

# import asyncio
# from typing import Any

# from src.app.settings import Settings


# class EmbeddingClient:
#     def __init__(self, settings: Settings):
#         self.settings = settings
#         self._model: Any | None = None
#         self._dim: int | None = None

#     async def embed_texts(self, texts: list[str]) -> list[list[float]]:
#         if not texts:
#             return []

#         await self._ensure_model()

#         def _encode() -> list[list[float]]:
#             eoutput = self._model.encode(  # type: ignore[union-attr]
#                 texts,
#                 batch_size=self.settings.embed_batch_size,
#                 max_length=self.settings.embed_max_length,
#                 return_dense=True,
#             )
#             dense = eoutput["dense_vecs"]
#             vecs = dense.tolist() if hasattr(dense, "tolist") else dense
#             return vecs

#         vecs = await asyncio.to_thread(_encode)
#         if vecs and self._dim is None:
#             self._dim = len(vecs[0])
#         return vecs

#     async def dim(self) -> int:
#         await self._ensure_model()
#         if self._dim is not None:
#             return self._dim
#         # If model not used yet, derive dim by embedding a tiny string.
#         vecs = await self.embed_texts(["dim_probe"])
#         return len(vecs[0]) if vecs else int(self.settings.embed_dim)

#     async def _ensure_model(self) -> None:
#         if self._model is not None:
#             return

#         def _load():
#             from FlagEmbedding import BGEM3FlagModel

#             return BGEM3FlagModel(
#                 self.settings.embed_model_path,
#                 use_fp16=self.settings.embed_use_fp16,
#                 use_bf16=self.settings.embed_use_bf16,
#                 device=self.settings.embed_device,
#                 batch_size=self.settings.embed_batch_size,
#                 query_max_length=self.settings.embed_max_length,
#             )

#         self._model = await asyncio.to_thread(_load)

from __future__ import annotations

import httpx
from aiolimiter import AsyncLimiter

from src.app.settings import Settings


class EmbeddingClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._client: httpx.AsyncClient | None = None
        # 每分钟最多 2000 次请求
        self._limiter = AsyncLimiter(2000, 60)

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url="https://api.siliconflow.cn/v1",
                headers={
                    "Authorization": f"Bearer {self.settings.llm_api_key}",
                    "Content-Type": "application/json",
                },
                timeout=30.0,
            )
        return self._client

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """批量获取文本向量，内部自动分批（每批最多 32 个）并遵守 RPM 限流"""
        if not texts:
            return []

        # 分批：每批最多 32 个文本
        batch_size = 32
        batches = [texts[i : i + batch_size] for i in range(0, len(texts), batch_size)]

        # 存储所有向量，保持原顺序
        all_embeddings = []

        client = await self._get_client()

        for batch in batches:
            # 速率限制：每个请求之前获取令牌
            async with self._limiter:
                response = await client.post(
                    "/embeddings",
                    json={
                        "input": batch,
                        "model": "BAAI/bge-m3",  # 或者从 settings 读取
                    },
                )
                response.raise_for_status()
                data = response.json()
                # API 返回的 data["data"] 顺序与 input 顺序一致
                batch_embeddings = [item["embedding"] for item in data["data"]]

                all_embeddings.extend(batch_embeddings)

        return all_embeddings

    async def close(self) -> None:
        """优雅关闭 HTTP 客户端"""
        if self._client:
            await self._client.aclose()
