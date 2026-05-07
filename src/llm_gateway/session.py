from __future__ import annotations

from typing import List, Dict, Any
from .config import SessionConfig


class ChatSession:
    def __init__(self, config: SessionConfig | None = None):
        self.config = config or SessionConfig()
        self.history: List[Dict[str, Any]] = []

    def add_message(self, role: str, content: Any):
        self.history.append(
            {
                "role": role,
                "content": content,
            }
        )
        self.trim_history()

    def trim_history(self):
        max_msgs = self.config.max_turns * 2
        if len(self.history) > max_msgs:
            self.history = self.history[-max_msgs:]

    def approx_token_count(self) -> int:
        total = 0
        for m in self.history:
            total += len(str(m.get("content", ""))) // 4
        return total

    def trim_by_token_budget(self):
        while (
            self.approx_token_count() > self.config.token_budget
            and len(self.history) > 2
        ):
            self.history.pop(0)
            self.history.pop(0)

    def get_history(self) -> List[Dict[str, Any]]:
        self.trim_history()
        self.trim_by_token_budget()
        return list(self.history)

    def clear(self):
        self.history.clear()
