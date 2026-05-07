from __future__ import annotations

import asyncio
import json

from sqlalchemy import select

from src.common.errors import RetryableError
from src.chunking.chunker import chunk_ir
from src.db.orm.file import File
from src.db.repo.chunk_repo import ChunkRepo
from src.db.repo.pipeline_repo import PipelineRepo
from src.mq.messages import FileEvent, PipelineStep
from src.mq.topology import ROUTING_EMBED
from src.parser.ir import DocumentIR
from src.workers._deps import db, rabbit, storage


async def handle_chunk(event: FileEvent) -> None:
    async with db().session() as session:
        p = PipelineRepo(session)
        started = await p.start_step(run_id=event.run_id, step=PipelineStep.CHUNK.value, attempt=event.attempt)
        if not started:
            return
        f = await session.scalar(select(File).where(File.file_id == event.file_id))
        if not f:
            raise RetryableError("file missing")
        ir_key = (f.meta_merged or {}).get("ir_key")
        if not ir_key:
            raise RetryableError("ir not ready")
        meta = dict(f.meta_merged or {})

    s3 = storage()

    def _get() -> bytes:
        obj = s3._client.get_object(Bucket=s3.settings.s3_bucket, Key=ir_key)
        return obj["Body"].read()

    ir = DocumentIR.from_jsonable(json.loads((await asyncio.to_thread(_get)).decode("utf-8")))
    chunks = chunk_ir(ir)

    async with db().session() as session:
        repo = ChunkRepo(session)
        await repo.insert_chunks(file_id=event.file_id, run_id=event.run_id, contents=chunks, payload_snapshot=meta)
        p = PipelineRepo(session)
        await p.ensure_step_row(run_id=event.run_id, file_id=event.file_id, step=PipelineStep.EMBED.value)
        await p.succeed_step(run_id=event.run_id, step=PipelineStep.CHUNK.value)

    await rabbit().publish(ROUTING_EMBED, FileEvent(file_id=event.file_id, run_id=event.run_id, step=PipelineStep.EMBED, attempt=0))

