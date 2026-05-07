from __future__ import annotations


def build_payload(*, file_id: str, meta: dict, chunk_index: int) -> dict:
    return {
        "fileuuid": file_id,
        "project": (meta.get("project") or ""),
        "company": (meta.get("company") or ""),
        "phase": (meta.get("phase") or ""),
        "category": (meta.get("category") or ""),
        "subcategory": (meta.get("subcategory") or ""),
        "chunk_index": chunk_index,
    }

