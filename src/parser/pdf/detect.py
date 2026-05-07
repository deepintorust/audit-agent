from __future__ import annotations

from src.parser.pdf.text_parser import PdfTextParser


def is_scanned_pdf(path: str, min_chars: int = 200) -> bool:
    # Heuristic: if text extraction yields very little text, treat as scanned.
    ir = PdfTextParser().parse(path)
    total = sum(len(b.text) for b in ir.blocks)
    return total < min_chars

