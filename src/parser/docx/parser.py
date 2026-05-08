from __future__ import annotations

from docx import Document

from src.parser.base import Parser
from src.parser.ir import Block, DocumentIR


class DocxParser(Parser):
    def parse(self, path: str) -> DocumentIR:
        doc = Document(path)
        blocks: list[Block] = []
        # First extract tables (rows) if any
        for table in doc.tables:
            for r_idx, row in enumerate(table.rows, start=1):
                cells = [(cell.text or "").strip() for cell in row.cells]
                # skip empty rows
                if not any(cells):
                    continue
                # join cells with full-width semicolon to keep readability
                text = "；".join(c for c in cells if c)
                blocks.append(Block(kind="table_row", text=text, meta={"row": r_idx}))

        # Then extract paragraph text (skip heading styles)
        for p in doc.paragraphs:
            text = (p.text or "").strip()
            if not text:
                continue
            style = (p.style.name or "").lower() if p.style else ""
            if style.startswith("heading"):
                continue
            blocks.append(Block(kind="paragraph", text=text, meta={}))
        return DocumentIR(blocks=blocks)
