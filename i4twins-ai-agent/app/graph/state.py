"""Shared LangGraph state (a Pydantic model; fresh for every request)."""
from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, Field


def merge_results(current: dict[str, str], new: dict[str, str]) -> dict[str, str]:
    return {**(current or {}), **(new or {})}


def concat_errors(current: list[str], new: list[str]) -> list[str]:
    return [*(current or []), *(new or [])]


class AgentState(BaseModel):
    original_prompt: str                      # never modified; every skill receives it
    normalized_prompt: str = ""               # for discovery / heuristics only
    detected_language: str = "unknown"
    # stage 1 - discovery
    candidate_skills: list[str] = Field(default_factory=list)
    registered_skill_count: int = 0
    discovery_strategy: str = "none"
    # stage 2 - routing
    selected_skills: list[str] = Field(default_factory=list)   # order = execution order
    depends_on_previous: bool = False         # True -> sequential, False -> parallel (2 skills)
    routing_confidence: float | None = None
    routing_source: Literal["llm", "fallback", "none"] = "none"
    routing_context_chars: int = 0            # size of the stage-2 LLM input
    reasoning_summary: str = ""
    routing_notes: list[str] = Field(default_factory=list)
    clarification_required: bool = False
    clarification_question: str | None = None
    unsupported_request: bool = False
    unsupported_reason: str | None = None
    # stage 3 - execution
    skill_results: Annotated[dict[str, str], merge_results] = Field(default_factory=dict)
    errors: Annotated[list[str], concat_errors] = Field(default_factory=list)
    final_response: str | None = None


class SkillTask(BaseModel):
    """Input of one `execute_skill` invocation: only what that skill needs."""

    skill_id: str
    prompt: str
    previous_output: str | None = None
    language: str = "unknown"
