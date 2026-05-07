from __future__ import annotations

from src.parser.ir import Block, DocumentIR


def fallback_parse_bytes(data: bytes) -> DocumentIR:
    txt = (data or b"").decode("utf-8", errors="ignore").strip()
    if not txt:
        return DocumentIR(blocks=[])
    return DocumentIR(blocks=[Block(kind="text", text=txt, meta={})])

