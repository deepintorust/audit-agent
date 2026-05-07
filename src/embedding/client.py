from __future__ import annotations

import asyncio
from typing import Any

from src.app.settings import Settings


class EmbeddingClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._model: Any | None = None
        self._dim: int | None = None

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        await self._ensure_model()

        def _encode() -> list[list[float]]:
            eoutput = self._model.encode(  # type: ignore[union-attr]
                texts,
                batch_size=self.settings.embed_batch_size,
                max_length=self.settings.embed_max_length,
                return_dense=True,
            )
            dense = eoutput["dense_vecs"]
            vecs = dense.tolist() if hasattr(dense, "tolist") else dense
            return vecs

        vecs = await asyncio.to_thread(_encode)
        if vecs and self._dim is None:
            self._dim = len(vecs[0])
        return vecs

    async def dim(self) -> int:
        await self._ensure_model()
        if self._dim is not None:
            return self._dim
        # If model not used yet, derive dim by embedding a tiny string.
        vecs = await self.embed_texts(["dim_probe"])
        return len(vecs[0]) if vecs else int(self.settings.embed_dim)

    async def _ensure_model(self) -> None:
        if self._model is not None:
            return

        def _load():
            from FlagEmbedding import BGEM3FlagModel

            return BGEM3FlagModel(
                self.settings.embed_model_path,
                use_fp16=self.settings.embed_use_fp16,
                use_bf16=self.settings.embed_use_bf16,
                device=self.settings.embed_device,
                batch_size=self.settings.embed_batch_size,
                query_max_length=self.settings.embed_max_length,
            )

        self._model = await asyncio.to_thread(_load)
