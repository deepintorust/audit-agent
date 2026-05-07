from __future__ import annotations

import hashlib
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile

from src.app.deps import db as db_dep, rabbit as rabbit_dep, storage as storage_dep
from src.common.ids import short_id_from_hash
from src.db.repo.file_repo import FileRepo
from src.mq.messages import FileEvent, PipelineStep
from src.mq.topology import ROUTING_STORE

router = APIRouter(prefix="/api/v1/document/submittal", tags=["files"])


@router.post("/upload")
async def upload_file(
    files: Annotated[list[UploadFile], File(...)],
    project: Annotated[str, Form()] = "",
    company: Annotated[str, Form()] = "",
    phase: Annotated[str, Form()] = "",
    category: Annotated[str, Form()] = "",
    subcategory: Annotated[str, Form()] = "",
    db=Depends(db_dep),
    rabbit=Depends(rabbit_dep),
    storage=Depends(storage_dep),
):
    results: list[dict[str, str]] = []
    for file in files:
        # Stream hash to avoid loading entire file into memory
        hasher = hashlib.sha256()
        tmp_path = await storage.write_upload_to_temp(file, hasher)
        file_hash_full = hasher.hexdigest()
        file_id = short_id_from_hash(file_hash_full)

        async with db.session() as session:
            repo = FileRepo(session)
            run_id = await repo.create_or_get_run(
                file_id=file_id,
                file_hash_full=file_hash_full,
                filename=file.filename or "",
                content_type=file.content_type or "",
                meta_frontend={
                    "project": project,
                    "company": company,
                    "phase": phase,
                    "category": category,
                    "subcategory": subcategory,
                },
            )

        # Store raw file in object storage (non-blocking CPU, but network-bound and required anyway)
        key = f"raw/{file_hash_full}"
        await storage.put_path(
            key=key, path=tmp_path, content_type=file.content_type or ""
        )
        await storage.remove_temp(tmp_path)

        async with db.session() as session:
            repo = FileRepo(session)
            await repo.set_storage(
                file_id=file_id,
                storage_backend="s3",
                bucket=storage.settings.s3_bucket,
                key=key,
            )

        event = FileEvent(
            file_id=file_id, run_id=run_id, step=PipelineStep.STORE, attempt=0
        )
        await rabbit.publish(ROUTING_STORE, event)
        results.append({"file_id": file_id, "run_id": run_id, "status": "processing"})

    return {"files": results}


@router.get("/{file_id}/status")
async def file_status(file_id: str, db=Depends(db_dep)):
    async with db.session() as session:
        repo = FileRepo(session)
        status = await repo.get_status(file_id)
    return status