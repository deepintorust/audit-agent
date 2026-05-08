from __future__ import annotations

try:
    import fitz  # PyMuPDF
except Exception:
    fitz = None

from pypdf import PdfReader

from src.parser.base import Parser
from src.parser.ir import Block, DocumentIR


class PdfTextParser(Parser):
    def parse(self, path: str) -> DocumentIR:
        # If PyMuPDF available, use its block-level extraction to capture table-like blocks.
        if fitz is not None:
            doc = fitz.open(path)
            blocks: list[Block] = []
            for i, page in enumerate(doc, start=1):
                b = page.get_text("blocks")
                if not b:
                    continue
                # each item: (x0, y0, x1, y1, "text", block_no)
                for item in b:
                    text = (item[4] or "").strip()
                    if not text:
                        continue
                    blocks.append(Block(kind="page_block", text=text, meta={"page": i}))
            return DocumentIR(blocks=blocks)

        # Fallback to pypdf simple text extraction per page
        reader = PdfReader(path)
        blocks: list[Block] = []
        for i, page in enumerate(reader.pages, start=1):
            txt = (page.extract_text() or "").strip()
            if not txt:
                continue
            blocks.append(Block(kind="page", text=txt, meta={"page": i}))
        return DocumentIR(blocks=blocks)
