from __future__ import annotations

from sqlalchemy import JSON, DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from src.db.orm.base import Base


class File(Base):
    __tablename__ = "files"

    file_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    file_hash_full: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    filename: Mapped[str] = mapped_column(Text)
    content_type: Mapped[str] = mapped_column(String(255), default="")

    # frontend values (truth source if provided)
    meta_frontend: Mapped[dict] = mapped_column(JSON, default=dict)
    # final merged values after fusion (may be partially empty)
    meta_merged: Mapped[dict] = mapped_column(JSON, default=dict)

    storage_backend: Mapped[str] = mapped_column(String(32), default="s3")
    storage_bucket: Mapped[str] = mapped_column(String(255), default="")
    storage_key: Mapped[str] = mapped_column(String(1024), default="")

    status: Mapped[str] = mapped_column(String(32), default="UPLOADED", index=True)
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

