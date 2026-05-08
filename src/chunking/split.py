from __future__ import annotations


def split_text_recursive(text: str, max_chars: int) -> list[str]:
    text = (text or "").strip()
    if not text:
        return []
    if len(text) <= max_chars:
        return [text]
    # Only split on double-newline paragraphs per new requirement.
    sep = "\n\n"
    if sep in text:
        parts = [p.strip() for p in text.split(sep) if p.strip()]
        out: list[str] = []
        buf = ""
        for p in parts:
            if not buf:
                buf = p
            elif len(buf) + 2 + len(p) <= max_chars:
                buf = f"{buf}{sep}{p}"
            else:
                out.extend(split_text_recursive(buf, max_chars))
                buf = p
        if buf:
            out.extend(split_text_recursive(buf, max_chars))
        return out

    # Fallback: hard cut if no double-newline paragraph separators
    return [text[i : i + max_chars] for i in range(0, len(text), max_chars)]
