from __future__ import annotations

from pathlib import Path


class PromptConfigError(RuntimeError):
    pass


def load_prompt_template_required(*, path: str | None, name: str) -> str:
    """
    Fail-fast variant: require a prompt template to be provided via a mounted file path.
    """
    if path:
        p = Path(path)
        if p.exists():
            content = p.read_text(encoding="utf-8").strip()
            if content:
                return content
        raise PromptConfigError(f"{name} template path not found or empty: {path}")
    raise PromptConfigError(f"{name} template path not configured (set {name}_PATH)")
