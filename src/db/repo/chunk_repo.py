from __future__ import annotations

import hashlib

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.orm.chunk import Chunk


class ChunkRepo:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def insert_chunks(
        self,
        *,
        file_id: str,
        run_id: str,
        contents: list[str],
        payload_snapshot: dict,
    ) -> int:
        inserted = 0
        for idx, content in enumerate(contents):
            chunk_id = hashlib.sha256(f"{file_id}:{idx}".encode("utf-8")).hexdigest()[:16]
            row = Chunk(
                chunk_id=chunk_id,
                file_id=file_id,
                run_id=run_id,
                chunk_index=idx,
                content=content,
                payload_snapshot=payload_snapshot,
                status="CHUNKED",
            )
            self.session.add(row)
            try:
                await self.session.flush()
                inserted += 1
            except IntegrityError:
                await self.session.rollback()
        await self.session.commit()
        return inserted

    async def list_by_status(self, *, file_id: str, run_id: str, status: str, limit: int = 5000) -> list[Chunk]:
        rows = (
            await self.session.execute(
                select(Chunk)
                .where(Chunk.file_id == file_id, Chunk.run_id == run_id, Chunk.status == status)
                .order_by(Chunk.chunk_index.asc())
                .limit(limit)
            )
        ).scalars().all()
        return list(rows)

    async def mark_status(self, *, file_id: str, run_id: str, chunk_indexes: list[int], status: str) -> None:
        if not chunk_indexes:
            return
        rows = (
            await self.session.execute(
                select(Chunk).where(Chunk.file_id == file_id, Chunk.run_id == run_id, Chunk.chunk_index.in_(chunk_indexes))
            )
        ).scalars().all()
        for r in rows:
            r.status = status
        await self.session.commit()

