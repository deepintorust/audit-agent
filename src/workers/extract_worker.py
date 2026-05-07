from __future__ import annotations

import asyncio
import json

from sqlalchemy import select

from src.common.errors import RetryableError
from src.db.orm.file import File
from src.db.repo.llm_log_repo import LlmLogRepo
from src.db.repo.pipeline_repo import PipelineRepo
from src.extraction.json_parse import parse_json_object
from src.extraction.schemas import ExtractionResult
from src.llm_gateway.schemas import ChatRequest
from src.mq.messages import FileEvent, PipelineStep
from src.mq.topology import ROUTING_FUSE
from src.parser.ir import DocumentIR
from src.common.prompting import load_prompt_template_required
from src.workers._deps import db, rabbit, settings, storage
from src.workers._llm import llm_client


def _slice_ir_text(ir: DocumentIR, max_chars: int = 8000) -> list[str]:
    # Join block texts into bounded slices to fit model context better.
    slices: list[str] = []
    buf = ""
    for b in ir.blocks:
        t = (b.text or "").strip()
        if not t:
            continue
        if not buf:
            buf = t
        elif len(buf) + 1 + len(t) <= max_chars:
            buf = f"{buf}\n{t}"
        else:
            slices.append(buf)
            buf = t
    if buf:
        slices.append(buf)
    return slices


async def handle_extract(event: FileEvent) -> None:
    async with db().session() as session:
        p = PipelineRepo(session)
        started = await p.start_step(run_id=event.run_id, step=PipelineStep.EXTRACT.value, attempt=event.attempt)
        if not started:
            return

        f = await session.scalar(select(File).where(File.file_id == event.file_id))
        if not f:
            raise RetryableError("file missing")
        ir_key = (f.meta_merged or {}).get("ir_key")
        if not ir_key:
            raise RetryableError("ir not ready")

    s3 = storage()

    def _get() -> bytes:
        obj = s3._client.get_object(Bucket=s3.settings.s3_bucket, Key=ir_key)
        return obj["Body"].read()

    raw = await asyncio.to_thread(_get)
    ir = DocumentIR.from_jsonable(json.loads(raw.decode("utf-8")))

    s = settings()
    text_slices = _slice_ir_text(ir)

    prompt_template = load_prompt_template_required(
        path=s.extract_prompt_template_path,
        name="EXTRACT_PROMPT_TEMPLATE",
    )

    chunk_candidates: list[dict] = []
    for idx, text in enumerate(text_slices):
        prompt = prompt_template.format(text=text[:8000])

        async with db().session() as session:
            log_repo = LlmLogRepo(session)
            call_id = await log_repo.start(
                run_id=event.run_id,
                file_id=event.file_id,
                step="EXTRACT",
                provider=s.llm_provider,
                model=s.llm_model,
                request_json={"slice_index": idx, "prompt": prompt[:2000]},
            )
        try:
            resp = await llm_client().chat(ChatRequest(prompt=prompt, json_mode=True))
            data = parse_json_object(resp)
            parsed = ExtractionResult.model_validate(data).model_dump()
            chunk_candidates.append(parsed)
            async with db().session() as session:
                log_repo = LlmLogRepo(session)
                await log_repo.finish_ok(call_id=call_id, response_json={"extraction": parsed})
        except Exception as e:  # noqa: BLE001
            async with db().session() as session:
                log_repo = LlmLogRepo(session)
                await log_repo.finish_err(call_id=call_id, error_msg=str(e))
            raise

    candidates_key = f"candidates/{event.file_id}/{event.run_id}.json"
    body = json.dumps({"chunks": chunk_candidates}, ensure_ascii=False).encode("utf-8")

    def _put() -> None:
        s3._client.put_object(Bucket=s3.settings.s3_bucket, Key=candidates_key, Body=body, ContentType="application/json")

    await asyncio.to_thread(_put)

    async with db().session() as session:
        f = await session.scalar(select(File).where(File.file_id == event.file_id))
        if f:
            merged = dict(f.meta_merged or {})
            merged["candidates_key"] = candidates_key
            f.meta_merged = merged
            f.status = "EXTRACTED"
        p = PipelineRepo(session)
        await p.ensure_step_row(run_id=event.run_id, file_id=event.file_id, step=PipelineStep.FUSE.value)
        await p.succeed_step(run_id=event.run_id, step=PipelineStep.EXTRACT.value)
        await session.commit()

    await rabbit().publish(ROUTING_FUSE, FileEvent(file_id=event.file_id, run_id=event.run_id, step=PipelineStep.FUSE, attempt=0))
