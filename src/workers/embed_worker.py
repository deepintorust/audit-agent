from __future__ import annotations

import asyncio
import json

from src.db.repo.chunk_repo import ChunkRepo
from src.db.repo.pipeline_repo import PipelineRepo
from src.app.deps import embedding
from src.mq.messages import FileEvent, PipelineStep
from src.mq.topology import ROUTING_INDEX
from src.workers._deps import db, rabbit, settings, storage


async def handle_embed(event: FileEvent) -> None:
    async with db().session() as session:
        p = PipelineRepo(session)
        started = await p.start_step(
            run_id=event.run_id, step=PipelineStep.EMBED.value, attempt=event.attempt
        )
        if not started:
            return

    s = settings()
    # reuse process-wide EmbeddingClient from deps (lru_cache singleton)
    embed = embedding()
    s3 = storage()

    async with db().session() as session:
        repo = ChunkRepo(session)
        chunks = await repo.list_by_status(
            file_id=event.file_id, run_id=event.run_id, status="CHUNKED"
        )
        if not chunks:
            # already embedded or no content
            p = PipelineRepo(session)
            await p.ensure_step_row(
                run_id=event.run_id,
                file_id=event.file_id,
                step=PipelineStep.INDEX.value,
            )
            await p.succeed_step(run_id=event.run_id, step=PipelineStep.EMBED.value)
            await session.commit()
            await rabbit().publish(
                ROUTING_INDEX,
                FileEvent(
                    file_id=event.file_id,
                    run_id=event.run_id,
                    step=PipelineStep.INDEX,
                    attempt=0,
                ),
            )
            return

    # Embed in batches; write embeddings artifact to S3
    emb_key = f"embeddings/{event.file_id}/{event.run_id}.jsonl"

    lines: list[bytes] = []
    idxs: list[int] = []
    for i in range(0, len(chunks), s.embed_batch_size):
        batch = chunks[i : i + s.embed_batch_size]
        vectors = await embed.embed_texts([c.content for c in batch])
        for c, v in zip(batch, vectors, strict=False):
            lines.append(
                json.dumps(
                    {"chunk_index": c.chunk_index, "vector": v}, ensure_ascii=False
                ).encode("utf-8")
                + b"\n"
            )
            idxs.append(c.chunk_index)

    body = b"".join(lines)

    def _put() -> None:
        s3._client.put_object(
            Bucket=s3.settings.s3_bucket,
            Key=emb_key,
            Body=body,
            ContentType="application/x-ndjson",
        )

    await asyncio.to_thread(_put)

    async with db().session() as session:
        repo = ChunkRepo(session)
        await repo.mark_status(
            file_id=event.file_id,
            run_id=event.run_id,
            chunk_indexes=idxs,
            status="EMBEDDED",
        )
        p = PipelineRepo(session)
        await p.ensure_step_row(
            run_id=event.run_id, file_id=event.file_id, step=PipelineStep.INDEX.value
        )
        await p.succeed_step(run_id=event.run_id, step=PipelineStep.EMBED.value)
        await session.commit()

    await rabbit().publish(
        ROUTING_INDEX,
        FileEvent(
            file_id=event.file_id,
            run_id=event.run_id,
            step=PipelineStep.INDEX,
            attempt=0,
        ),
    )
