from __future__ import annotations

from abc import ABC, abstractmethod

from src.parser.ir import DocumentIR


class Parser(ABC):
    @abstractmethod
    def parse(self, path: str) -> DocumentIR: ...

