from __future__ import annotations

from docx import Document

from src.parser.base import Parser
from src.parser.ir import Block, DocumentIR


class DocxParser(Parser):
    def parse(self, path: str) -> DocumentIR:
        doc = Document(path)
        blocks: list[Block] = []
        heading_path: list[str] = []
        for p in doc.paragraphs:
            text = (p.text or "").strip()
            if not text:
                continue
            style = (p.style.name or "").lower() if p.style else ""
            if style.startswith("heading"):
                # best-effort heading level detection
                heading_path = heading_path[:0]
                heading_path.append(text)
                blocks.append(Block(kind="heading", text=text, meta={"heading_path": list(heading_path)}))
            else:
                blocks.append(Block(kind="paragraph", text=text, meta={"heading_path": list(heading_path)}))
        return DocumentIR(blocks=blocks)

