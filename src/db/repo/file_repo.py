from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.orm.file import File
from src.db.orm.pipeline_run import PipelineRun
from src.db.orm.process_step import ProcessStep


class FileRepo:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_or_get_run(
        self,
        *,
        file_id: str,
        file_hash_full: str,
        filename: str,
        content_type: str,
        meta_frontend: dict,
    ) -> str:
        existing = await self.session.scalar(select(File).where(File.file_hash_full == file_hash_full))
        if existing:
            # Deduplicate by full hash: return existing latest run
            run = await self.session.scalar(
                select(PipelineRun).where(PipelineRun.file_id == existing.file_id).order_by(PipelineRun.created_at.desc())
            )
            return run.run_id if run else str(uuid.uuid4())

        f = File(
            file_id=file_id,
            file_hash_full=file_hash_full,
            filename=filename,
            content_type=content_type,
            meta_frontend=meta_frontend,
            meta_merged={},
            status="UPLOADED",
        )
        self.session.add(f)

        run_id = str(uuid.uuid4())
        run = PipelineRun(run_id=run_id, file_id=file_id, status="RUNNING", current_step="STORE")
        self.session.add(run)

        self.session.add(
            ProcessStep(run_id=run_id, file_id=file_id, step="STORE", status="PENDING", attempt=0)
        )
        await self.session.commit()
        return run_id

    async def set_storage(self, *, file_id: str, storage_backend: str, bucket: str, key: str) -> None:
        f = await self.session.scalar(select(File).where(File.file_id == file_id))
        if not f:
            return
        f.storage_backend = storage_backend
        f.storage_bucket = bucket
        f.storage_key = key
        f.status = "STORED"
        await self.session.commit()

    async def get_status(self, file_id: str) -> dict:
        f = await self.session.scalar(select(File).where(File.file_id == file_id))
        if not f:
            return {"file_id": file_id, "exists": False}
        run = await self.session.scalar(
            select(PipelineRun).where(PipelineRun.file_id == file_id).order_by(PipelineRun.created_at.desc())
        )
        steps = []
        if run:
            rows = (await self.session.execute(select(ProcessStep).where(ProcessStep.run_id == run.run_id))).scalars().all()
            steps = [
                {"step": r.step, "status": r.status, "attempt": r.attempt, "error_code": r.error_code, "error_msg": r.error_msg}
                for r in rows
            ]
        return {
            "file_id": file_id,
            "exists": True,
            "file_status": f.status,
            "run_id": run.run_id if run else None,
            "run_status": run.status if run else None,
            "current_step": run.current_step if run else None,
            "steps": steps,
            "meta_frontend": f.meta_frontend,
            "meta_merged": f.meta_merged,
        }
