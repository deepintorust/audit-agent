from __future__ import annotations

import asyncio
import os
import json
import tempfile

from src.common.errors import RetryableError
from src.db.repo.pipeline_repo import PipelineRepo
from src.db.repo.llm_log_repo import LlmLogRepo
from src.mq.messages import FileEvent, PipelineStep
from src.mq.topology import ROUTING_EXTRACT
from src.llm_gateway.schemas import ChatRequest
from src.parser.docx.parser import DocxParser
from src.parser.pdf.detect import is_scanned_pdf
from src.parser.pdf.image_render import render_pdf_pages_to_images
from src.parser.pdf.text_parser import PdfTextParser
from src.parser.xlsx.parser import XlsxParser
from src.parser.fallback import fallback_parse_bytes
from src.storage.s3 import S3Storage
from src.workers._deps import db, rabbit, settings, storage
from src.workers._llm import llm_client
from src.parser.ir import Block, DocumentIR


def _suffix(filename: str) -> str:
    return os.path.splitext(filename or "")[1].lower()


async def _download_to_temp(s3: S3Storage, key: str) -> str:
    # boto3 doesn't have native async; use thread.
    fd, path = tempfile.mkstemp(prefix="audit-raw-", suffix=".bin")
    os.close(fd)

    def _dl() -> None:
        s3._client.download_file(Bucket=s3.settings.s3_bucket, Key=key, Filename=path)

    import asyncio

    await asyncio.to_thread(_dl)
    return path


async def handle_parse(event: FileEvent) -> None:
    async with db().session() as session:
        p = PipelineRepo(session)
        started = await p.start_step(
            run_id=event.run_id, step=PipelineStep.PARSE.value, attempt=event.attempt
        )
        if not started:
            return

    # Fetch file record to know storage key & filename
    from sqlalchemy import select
    from src.db.orm.file import File

    async with db().session() as session:
        f = await session.scalar(select(File).where(File.file_id == event.file_id))
        if not f or not f.storage_key:
            raise RetryableError("file not stored yet")
        key = f.storage_key
        filename = f.filename

    s3 = storage()
    local = await _download_to_temp(s3, key)
    ext = _suffix(filename)
    if ext == ".pdf":
        if is_scanned_pdf(local):
            # Multimodal OCR per page, then merge into page blocks.
            img_paths = render_pdf_pages_to_images(local)
            sem = asyncio.Semaphore(settings().llm_max_concurrency)

            async def _ocr_one(page_no: int, img_path: str) -> str:
                async with sem:
                    img_bytes = await asyncio.to_thread(
                        lambda: open(img_path, "rb").read()
                    )
                    prompt = "请识别图片中的文字内容，直接输出纯文本，尽量保留段落换行，不要添加解释。"
                    # log start
                    async with db().session() as session:
                        log_repo = LlmLogRepo(session)
                        call_id = await log_repo.start(
                            run_id=event.run_id,
                            file_id=event.file_id,
                            step="PARSE_OCR",
                            provider=settings().llm_provider,
                            model=settings().vlm_model or settings().llm_model,
                            request_json={"page": page_no, "prompt": prompt},
                        )
                    try:
                        text = await llm_client().chat(
                            ChatRequest(
                                prompt=prompt, json_mode=False, image_bytes=img_bytes
                            )
                        )
                        async with db().session() as session:
                            log_repo = LlmLogRepo(session)
                            await log_repo.finish_ok(
                                call_id=call_id, response_json={"text": text}
                            )
                        return text
                    except Exception as e:  # noqa: BLE001
                        async with db().session() as session:
                            log_repo = LlmLogRepo(session)
                            await log_repo.finish_err(call_id=call_id, error_msg=str(e))
                        raise

            texts = await asyncio.gather(
                *[_ocr_one(i + 1, p) for i, p in enumerate(img_paths)]
            )
            for p in img_paths:
                try:
                    os.remove(p)
                except OSError:
                    pass
            blocks = [
                Block(
                    kind="page", text=t.strip(), meta={"page": i + 1, "source": "vlm"}
                )
                for i, t in enumerate(texts)
                if (t or "").strip()
            ]
            ir = DocumentIR(blocks=blocks)
        else:
            ir = PdfTextParser().parse(local)
    elif ext == ".docx":
        ir = DocxParser().parse(local)
    elif ext == ".xlsx":
        ir = XlsxParser().parse(local)
    else:
        with open(local, "rb") as f:
            ir = fallback_parse_bytes(f.read())

    os.remove(local)

    # Store IR as JSON in S3

    ir_key = f"ir/{event.file_id}/{event.run_id}.json"
    body = json.dumps(ir.to_jsonable(), ensure_ascii=False).encode("utf-8")

    def _upload() -> None:
        s3._client.put_object(
            Bucket=s3.settings.s3_bucket,
            Key=ir_key,
            Body=body,
            ContentType="application/json",
        )

    await asyncio.to_thread(_upload)

    async with db().session() as session:
        from src.db.orm.file import File
        from sqlalchemy import select

        f = await session.scalar(select(File).where(File.file_id == event.file_id))
        if f:
            merged = dict(f.meta_merged or {})
            merged["ir_key"] = ir_key
            f.meta_merged = merged
            f.status = "PARSED"
        p = PipelineRepo(session)
        await p.ensure_step_row(
            run_id=event.run_id, file_id=event.file_id, step=PipelineStep.EXTRACT.value
        )
        await p.succeed_step(run_id=event.run_id, step=PipelineStep.PARSE.value)
        await session.commit()

    await rabbit().publish(
        ROUTING_EXTRACT,
        FileEvent(
            file_id=event.file_id,
            run_id=event.run_id,
            step=PipelineStep.EXTRACT,
            attempt=0,
        ),
    )
