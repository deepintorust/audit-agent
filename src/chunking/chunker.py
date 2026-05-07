from __future__ import annotations

from src.chunking.split import split_text_recursive
from src.parser.ir import DocumentIR


def chunk_ir(
    ir: DocumentIR,
    *,
    target_chars: int = 1200,
    overlap_chars: int = 200,
) -> list[str]:
    # Start from block texts, keep order, then pack into chunks.
    texts: list[str] = []
    for b in ir.blocks:
        t = (b.text or "").strip()
        if not t:
            continue
        texts.extend(split_text_recursive(t, target_chars))

    chunks: list[str] = []
    buf = ""
    for t in texts:
        if not buf:
            buf = t
            continue
        if len(buf) + 2 + len(t) <= target_chars:
            buf = f"{buf}\n{t}"
        else:
            chunks.append(buf)
            if overlap_chars > 0 and len(buf) > overlap_chars:
                buf = buf[-overlap_chars:] + "\n" + t
            else:
                buf = t
    if buf:
        chunks.append(buf)
    return chunks

