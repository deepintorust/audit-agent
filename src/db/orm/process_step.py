from __future__ import annotations

from sqlalchemy import DateTime, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from src.db.orm.base import Base


class ProcessStep(Base):
    __tablename__ = "process_steps"
    __table_args__ = (UniqueConstraint("run_id", "step", name="uq_run_step"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(36), index=True)
    file_id: Mapped[str] = mapped_column(String(32), index=True)
    step: Mapped[str] = mapped_column(String(16), index=True)
    status: Mapped[str] = mapped_column(String(16), default="PENDING", index=True)
    attempt: Mapped[int] = mapped_column(Integer, default=0)
    error_code: Mapped[str] = mapped_column(String(64), default="")
    error_msg: Mapped[str] = mapped_column(Text, default="")
    started_at: Mapped[str] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[str] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

