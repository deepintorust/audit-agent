from __future__ import annotations

import os
import tempfile

import fitz  # PyMuPDF


def render_pdf_pages_to_images(path: str) -> list[str]:
    doc = fitz.open(path)
    out_paths: list[str] = []
    for i in range(doc.page_count):
        page = doc.load_page(i)
        pix = page.get_pixmap(dpi=200)
        fd, out = tempfile.mkstemp(prefix="audit-page-", suffix=".png")
        os.close(fd)
        pix.save(out)
        out_paths.append(out)
    return out_paths

