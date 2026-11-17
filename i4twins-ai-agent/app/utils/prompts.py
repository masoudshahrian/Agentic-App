"""Prompt loading with access tracking.

Full skill prompts are loaded lazily, only when a skill executes. `PromptStore.accessed`
records every prompt name that was actually loaded, which the tests and the scalability
simulation use to prove that unselected skills' prompts are never touched.
"""
from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

PROMPT_DIR = Path(__file__).resolve().parent.parent / "prompts"


class PromptStore:
    def __init__(self, source: Callable[[str], str]) -> None:
        self._source = source
        self._cache: dict[str, str] = {}
        self.accessed: set[str] = set()

    def load(self, name: str) -> str:
        self.accessed.add(name)
        if name not in self._cache:
            self._cache[name] = self._source(name)
        return self._cache[name]

    def reset_access_log(self) -> None:
        self.accessed.clear()


def _read_file(name: str) -> str:
    return (PROMPT_DIR / f"{name}.txt").read_text(encoding="utf-8").strip()


default_store = PromptStore(_read_file)


def load_prompt(name: str) -> str:
    """Load a prompt file from app/prompts through the shared, tracked store."""
    return default_store.load(name)
