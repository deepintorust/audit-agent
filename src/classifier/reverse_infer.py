from __future__ import annotations

from src.classifier.mapping_loader import ClassificationMapping


def infer_phase_category(mapping: ClassificationMapping, subcategory: str) -> tuple[str, str]:
    sub = (subcategory or "").strip()
    if not sub:
        return "", ""
    return mapping.reverse.get(sub, ("", ""))

