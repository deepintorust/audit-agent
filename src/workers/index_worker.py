from __future__ import annotations

import asyncio
import json

from sqlalchemy import select

from src.common.errors import RetryableError
from src.db.orm.file import File
from src.db.repo.chunk_repo import ChunkRepo
from src.db.repo.pipeline_repo import PipelineRepo
from src.mq.messages import FileEvent, PipelineStep
from src.vectorstore.payload import build_payload
from src.workers._deps import db, qdrant, storage


async def handle_index(event: FileEvent) -> None:
    async with db().session() as session:
        p = PipelineRepo(session)
        started = await p.start_step(run_id=event.run_id, step=PipelineStep.INDEX.value, attempt=event.attempt)
        if not started:
            return
        f = await session.scalar(select(File).where(File.file_id == event.file_id))
        if not f:
            raise RetryableError("file missing")
        meta = dict(f.meta_merged or {})

    s3 = storage()
    emb_key = f"embeddings/{event.file_id}/{event.run_id}.jsonl"

    def _get_lines() -> list[bytes]:
        obj = s3._client.get_object(Bucket=s3.settings.s3_bucket, Key=emb_key)
        return obj["Body"].read().splitlines()

    try:
        lines = await asyncio.to_thread(_get_lines)
    except Exception as e:  # noqa: BLE001
        raise RetryableError(f"embeddings not ready: {e}") from e

    store = qdrant()
    # Startup init is responsible for creating collections and payload indexes.
    if not store.client.collection_exists(store.settings.qdrant_collection):
        raise RetryableError("qdrant collection not initialized yet")

    points = []
    chunk_indexes: list[int] = []
    for line in lines:
        rec = json.loads(line)
        chunk_index = int(rec["chunk_index"])
        vector = rec["vector"]
        point_id = f"{event.file_id}-{chunk_index}"
        payload = build_payload(file_id=event.file_id, meta=meta, chunk_index=chunk_index)
        points.append((point_id, vector, payload))
        chunk_indexes.append(chunk_index)

    def _upsert() -> None:
        store.client.upsert(
            collection_name=store.settings.qdrant_collection,
            points=[
                {"id": pid, "vector": vec, "payload": payload}  # qdrant-client accepts dicts
                for pid, vec, payload in points
            ],
        )

    await asyncio.to_thread(_upsert)

    async with db().session() as session:
        repo = ChunkRepo(session)
        await repo.mark_status(file_id=event.file_id, run_id=event.run_id, chunk_indexes=chunk_indexes, status="INDEXED")
        p = PipelineRepo(session)
        await p.succeed_step(run_id=event.run_id, step=PipelineStep.INDEX.value)
        await p.mark_run_done(run_id=event.run_id)
        await session.commit()
