from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.db.orm.llm_call_log import LlmCallLog


class LlmLogRepo:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def start(
        self,
        *,
        run_id: str,
        file_id: str,
        step: str,
        provider: str,
        model: str,
        request_json: dict,
    ) -> str:
        call_id = str(uuid.uuid4())
        row = LlmCallLog(
            call_id=call_id,
            run_id=run_id,
            file_id=file_id,
            step=step,
            provider=provider,
            model=model,
            request_json=request_json,
            response_json={},
            error_msg="",
            success=0,
            started_at=datetime.now(timezone.utc),
            ended_at=None,
        )
        self.session.add(row)
        await self.session.commit()
        return call_id

    async def finish_ok(self, *, call_id: str, response_json: dict) -> None:
        row = await self.session.scalar(select(LlmCallLog).where(LlmCallLog.call_id == call_id))
        if not row:
            return
        row.response_json = response_json
        row.success = 1
        row.error_msg = ""
        row.ended_at = datetime.now(timezone.utc)
        await self.session.commit()

    async def finish_err(self, *, call_id: str, error_msg: str, response_json: dict | None = None) -> None:
        row = await self.session.scalar(select(LlmCallLog).where(LlmCallLog.call_id == call_id))
        if not row:
            return
        if response_json is not None:
            row.response_json = response_json
        row.success = 0
        row.error_msg = error_msg
        row.ended_at = datetime.now(timezone.utc)
        await self.session.commit()
