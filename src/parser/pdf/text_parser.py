from __future__ import annotations

from pypdf import PdfReader

from src.parser.base import Parser
from src.parser.ir import Block, DocumentIR


class PdfTextParser(Parser):
    def parse(self, path: str) -> DocumentIR:
        reader = PdfReader(path)
        blocks: list[Block] = []
        for i, page in enumerate(reader.pages, start=1):
            txt = (page.extract_text() or "").strip()
            if not txt:
                continue
            blocks.append(Block(kind="page", text=txt, meta={"page": i}))
        return DocumentIR(blocks=blocks)

