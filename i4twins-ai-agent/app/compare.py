"""Run one request through one or several models in parallel and collect comparable results."""
from __future__ import annotations

import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field, replace

from app.graph import AgentState


@dataclass(frozen=True)
class ModelResult:
    model_id: str
    answer: str = ""
    skills: str = ""
    language: str = ""
    kind: str = "answer"  # answer | clarification | unsupported | error
    warnings: list[str] = field(default_factory=list)
    seconds: float = 0.0


def _describe(model_id: str, state: AgentState) -> ModelResult:
    skills = " + ".join(state.selected_skills) or "none"
    if len(state.selected_skills) == 2:
        skills += " (sequential)" if state.depends_on_previous else " (parallel)"
    kind = "clarification" if state.clarification_required else "unsupported" if state.unsupported_request else "answer"
    return ModelResult(model_id, state.final_response or "", skills, state.detected_language, kind, list(state.errors))


def run_models(prompt: str, model_ids: list[str], run_one: Callable[[str, str], AgentState]) -> list[ModelResult]:
    """Call ``run_one(model_id, prompt)`` for every model concurrently; a failing model never hides the others."""
    def safe(model_id: str) -> ModelResult:
        started = time.perf_counter()
        try:
            result = _describe(model_id, run_one(model_id, prompt))
        except Exception as exc:  # config/network problems are shown per model
            result = ModelResult(model_id, f"{type(exc).__name__}: {exc}", kind="error")
        return replace(result, seconds=round(time.perf_counter() - started, 1))

    with ThreadPoolExecutor(max_workers=max(1, len(model_ids))) as pool:
        return list(pool.map(safe, model_ids))
