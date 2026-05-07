from __future__ import annotations

from dataclasses import dataclass

import yaml


@dataclass(frozen=True)
class ClassificationMapping:
    # subcategory -> (phase, category)
    reverse: dict[str, tuple[str, str]]


def load_mapping(path: str) -> ClassificationMapping:
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    reverse: dict[str, tuple[str, str]] = {}
    for p in data.get("phases", []) or []:
        phase = (p.get("phase") or "").strip()
        for c in p.get("categories", []) or []:
            category = (c.get("category") or "").strip()
            for sub in c.get("subcategories", []) or []:
                sub_s = (str(sub) or "").strip()
                if not sub_s:
                    continue
                reverse[sub_s] = (phase, category)
    return ClassificationMapping(reverse=reverse)

