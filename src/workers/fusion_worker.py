from __future__ import annotations

import asyncio
import json

from sqlalchemy import select

from src.common.errors import RetryableError
from src.db.orm.file import File
from src.db.repo.pipeline_repo import PipelineRepo
from src.mq.messages import FileEvent, PipelineStep
from src.mq.topology import ROUTING_CHUNK
from src.workers._deps import db, rabbit, settings, storage
from src.classifier.mapping_loader import load_mapping
from src.classifier.reverse_infer import infer_phase_category


async def handle_fuse(event: FileEvent) -> None:
    async with db().session() as session:
        p = PipelineRepo(session)
        started = await p.start_step(run_id=event.run_id, step=PipelineStep.FUSE.value, attempt=event.attempt)
        if not started:
            return

        f = await session.scalar(select(File).where(File.file_id == event.file_id))
        if not f:
            raise RetryableError("file missing")
        candidates_key = (f.meta_merged or {}).get("candidates_key")
        if not candidates_key:
            raise RetryableError("candidates not ready")

    s3 = storage()

    def _get() -> bytes:
        obj = s3._client.get_object(Bucket=s3.settings.s3_bucket, Key=candidates_key)
        return obj["Body"].read()

    candidates = json.loads((await asyncio.to_thread(_get)).decode("utf-8"))
    chunks: list[dict] = list(candidates.get("chunks") or [])

    async with db().session() as session:
        f = await session.scalar(select(File).where(File.file_id == event.file_id))
        if not f:
            raise RetryableError("file missing")

        merged = dict(f.meta_merged or {})
        frontend = dict(f.meta_frontend or {})

        def _first_non_empty(path: tuple[str, str]) -> str:
            a, b = path
            for c in chunks:
                section = c.get(a)
                if not isinstance(section, dict):
                    continue
                v = section.get(b)
                if isinstance(v, str) and v.strip():
                    return v.strip()
            return ""

        # 1) Frontend truth source for file five attributes.
        for k in ["project", "company", "phase", "category", "subcategory"]:
            if (frontend.get(k) or "").strip():
                merged[k] = frontend[k].strip()
            else:
                merged[k] = _first_non_empty(("file", k))

        # 2) If LLM found subcategory, reverse infer phase/category from mapping.
        if merged.get("subcategory") and (not merged.get("phase") or not merged.get("category")):
            mapping = load_mapping(settings().classification_mapping_path)
            ph, cat = infer_phase_category(mapping, merged.get("subcategory", ""))
            if ph and not merged.get("phase"):
                merged["phase"] = ph
            if cat and not merged.get("category"):
                merged["category"] = cat

        f.meta_merged = merged
        f.status = "FUSED"
        p = PipelineRepo(session)
        await p.ensure_step_row(run_id=event.run_id, file_id=event.file_id, step=PipelineStep.CHUNK.value)
        await p.succeed_step(run_id=event.run_id, step=PipelineStep.FUSE.value)
        await session.commit()

    await rabbit().publish(ROUTING_CHUNK, FileEvent(file_id=event.file_id, run_id=event.run_id, step=PipelineStep.CHUNK, attempt=0))
