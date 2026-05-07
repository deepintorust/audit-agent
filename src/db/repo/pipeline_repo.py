from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.orm.pipeline_run import PipelineRun
from src.db.orm.process_step import ProcessStep


class PipelineRepo:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def ensure_step_row(self, *, run_id: str, file_id: str, step: str) -> None:
        row = await self.session.scalar(select(ProcessStep).where(ProcessStep.run_id == run_id, ProcessStep.step == step))
        if row:
            return
        self.session.add(ProcessStep(run_id=run_id, file_id=file_id, step=step, status="PENDING", attempt=0))
        await self.session.commit()

    async def start_step(self, *, run_id: str, step: str, attempt: int) -> bool:
        row = await self.session.scalar(select(ProcessStep).where(ProcessStep.run_id == run_id, ProcessStep.step == step))
        if not row:
            return False
        if row.status == "SUCCEEDED":
            return False
        row.status = "RUNNING"
        row.attempt = attempt
        row.started_at = datetime.now(timezone.utc)
        await self._set_current_step(run_id, step)
        await self.session.commit()
        return True

    async def succeed_step(self, *, run_id: str, step: str) -> None:
        row = await self.session.scalar(select(ProcessStep).where(ProcessStep.run_id == run_id, ProcessStep.step == step))
        if not row:
            return
        row.status = "SUCCEEDED"
        row.ended_at = datetime.now(timezone.utc)
        await self.session.commit()

    async def fail_step(self, *, run_id: str, step: str, error_code: str, error_msg: str) -> None:
        row = await self.session.scalar(select(ProcessStep).where(ProcessStep.run_id == run_id, ProcessStep.step == step))
        if not row:
            return
        row.status = "FAILED"
        row.error_code = error_code
        row.error_msg = error_msg
        row.ended_at = datetime.now(timezone.utc)

        run = await self.session.scalar(select(PipelineRun).where(PipelineRun.run_id == run_id))
        if run:
            run.status = "FAILED"
            run.current_step = step

        await self.session.commit()

    async def mark_run_done(self, *, run_id: str) -> None:
        run = await self.session.scalar(select(PipelineRun).where(PipelineRun.run_id == run_id))
        if not run:
            return
        run.status = "DONE"
        run.current_step = "DONE"
        await self.session.commit()

    async def _set_current_step(self, run_id: str, step: str) -> None:
        run = await self.session.scalar(select(PipelineRun).where(PipelineRun.run_id == run_id))
        if not run:
            return
        run.current_step = step

