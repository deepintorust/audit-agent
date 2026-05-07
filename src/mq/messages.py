from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel


class PipelineStep(StrEnum):
    STORE = "STORE"
    PARSE = "PARSE"
    EXTRACT = "EXTRACT"
    FUSE = "FUSE"
    CHUNK = "CHUNK"
    EMBED = "EMBED"
    INDEX = "INDEX"


class FileEvent(BaseModel):
    file_id: str
    run_id: str
    step: PipelineStep
    attempt: int = 0

