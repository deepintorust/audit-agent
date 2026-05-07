from __future__ import annotations

import asyncio
import json
import uuid

from sqlalchemy import select

from src.common.errors import FatalError, RetryableError
from src.db.orm.chunk import Chunk
from src.db.orm.file import File
from src.db.repo.chunk_repo import ChunkRepo
from src.db.repo.pipeline_repo import PipelineRepo
from src.mq.messages import FileEvent, PipelineStep
from src.vectorstore.payload import build_payload
from src.workers._deps import db, qdrant, storage


def _build_point_id(file_id: str, chunk_index: int) -> str:
    """Build a deterministic UUID point id accepted by Qdrant."""
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"{file_id}:{chunk_index}"))


def _collection_vector_size(store, collection_name: str) -> int | None:
    info = store.client.get_collection(collection_name=collection_name)
    cfg = getattr(info, "config", None)
    params = getattr(cfg, "params", None)
    vectors = getattr(params, "vectors", None)
    if vectors is None:
        return None
    if hasattr(vectors, "size"):
        return int(vectors.size)
    if isinstance(vectors, dict):
        first = next(iter(vectors.values()), None)
        if first is not None and hasattr(first, "size"):
            return int(first.size)
    return None


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
    chunk_vectors: list[tuple[int, list[float]]] = []
    expected_dim = _collection_vector_size(store, store.settings.qdrant_collection)
    for line in lines:
        rec = json.loads(line)
        chunk_index = int(rec["chunk_index"])
        vector = rec["vector"]
        if not isinstance(vector, list) or not vector:
            raise FatalError(f"invalid embedding vector for chunk_index={chunk_index}")
        if expected_dim is not None and len(vector) != expected_dim:
            raise FatalError(
                f"embedding dim mismatch for chunk_index={chunk_index}: got {len(vector)}, expected {expected_dim}"
            )
        chunk_vectors.append((chunk_index, vector))
        chunk_indexes.append(chunk_index)

    async with db().session() as session:
        rows = (
            await session.execute(
                select(Chunk).where(
                    Chunk.file_id == event.file_id,
                    Chunk.run_id == event.run_id,
                    Chunk.chunk_index.in_(chunk_indexes)
                )
            )
        ).scalars().all()
        chunk_content_by_index = {int(r.chunk_index): r.content for r in rows}

    for chunk_index, vector in chunk_vectors:
        point_id = _build_point_id(event.file_id, chunk_index)
        payload = build_payload(
            file_id=event.file_id,
            meta=meta,
            chunk_index=chunk_index,
            content=chunk_content_by_index.get(chunk_index, ""),
        )
        points.append((point_id, vector, payload))

    def _upsert() -> None:
        store.client.upsert(
            collection_name=store.settings.qdrant_collection,
            points=[
                {"id": pid, "vector": vec, "payload": payload}
                for pid, vec, payload in points
            ],
        )

    try:
        await asyncio.to_thread(_upsert)
    except Exception as e:  # noqa: BLE001
        async with db().session() as session:
            p = PipelineRepo(session)
            await p.fail_step(run_id=event.run_id, step=PipelineStep.INDEX.value, error_code="INDEX_UPSERT_FAILED", error_msg=str(e)[:500])
        raise

    async with db().session() as session:
        repo = ChunkRepo(session)
        await repo.mark_status(file_id=event.file_id, run_id=event.run_id, chunk_indexes=chunk_indexes, status="INDEXED")
        p = PipelineRepo(session)
        await p.succeed_step(run_id=event.run_id, step=PipelineStep.INDEX.value)
        await p.mark_run_done(run_id=event.run_id)
        await session.commit()