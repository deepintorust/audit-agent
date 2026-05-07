from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Block:
    kind: str
    text: str
    meta: dict


@dataclass(frozen=True)
class DocumentIR:
    blocks: list[Block]

    def to_jsonable(self) -> dict:
        return {
            "blocks": [{"kind": b.kind, "text": b.text, "meta": b.meta} for b in self.blocks],
        }

    @classmethod
    def from_jsonable(cls, d: dict) -> "DocumentIR":
        blocks = [Block(kind=x["kind"], text=x["text"], meta=x.get("meta", {})) for x in d.get("blocks", [])]
        return cls(blocks=blocks)

