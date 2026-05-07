from __future__ import annotations

from src.db.repo.pipeline_repo import PipelineRepo
from src.mq.messages import FileEvent, PipelineStep
from src.mq.topology import ROUTING_PARSE
from src.workers._deps import db, rabbit


async def handle_store(event: FileEvent) -> None:
    async with db().session() as session:
        repo = PipelineRepo(session)
        started = await repo.start_step(run_id=event.run_id, step=PipelineStep.STORE.value, attempt=event.attempt)
        if not started:
            return
        await repo.ensure_step_row(run_id=event.run_id, file_id=event.file_id, step=PipelineStep.PARSE.value)
        await repo.succeed_step(run_id=event.run_id, step=PipelineStep.STORE.value)

    await rabbit().publish(ROUTING_PARSE, FileEvent(file_id=event.file_id, run_id=event.run_id, step=PipelineStep.PARSE, attempt=0))

