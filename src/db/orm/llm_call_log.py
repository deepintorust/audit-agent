from __future__ import annotations

from sqlalchemy import DateTime, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from src.db.orm.base import Base


class LlmCallLog(Base):
    __tablename__ = "llm_call_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    call_id: Mapped[str] = mapped_column(String(36), index=True)
    run_id: Mapped[str] = mapped_column(String(36), index=True)
    file_id: Mapped[str] = mapped_column(String(32), index=True)
    step: Mapped[str] = mapped_column(String(16), index=True)

    provider: Mapped[str] = mapped_column(String(64), default="")
    model: Mapped[str] = mapped_column(String(128), default="")
    request_json: Mapped[dict] = mapped_column(JSON, default=dict)
    response_json: Mapped[dict] = mapped_column(JSON, default=dict)
    error_msg: Mapped[str] = mapped_column(Text, default="")
    success: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())
    ended_at: Mapped[str] = mapped_column(DateTime(timezone=True), nullable=True)

