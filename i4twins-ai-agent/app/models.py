"""Models the user can pick in the UI. Ids are OpenRouter ids; nothing here is skill-specific."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ModelChoice:
    label: str
    model_id: str
    note: str


# All <= 35B parameters. OpenRouter currently lists no free Qwen model, so the Qwen entry is a paid (cheap) one.
MODEL_CHOICES: tuple[ModelChoice, ...] = (
    ModelChoice("Gemma 4 31B", "google/gemma-4-31b-it", "paid, very cheap; used for the measured evaluation"),
    ModelChoice("Gemma 4 31B (free)", "google/gemma-4-31b-it:free", "free, often rate-limited upstream"),
    ModelChoice("Qwen3 32B", "qwen/qwen3-32b", "paid, cheap (no free Qwen is available on OpenRouter)"),
)


def choice_by_label(label: str) -> ModelChoice:
    for choice in MODEL_CHOICES:
        if choice.label == label:
            return choice
    raise KeyError(label)
