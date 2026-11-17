"""Synthetic skill registry for the scalability simulation and tests.

These skills exist ONLY here (never in the real application). Each one has compact routing
metadata and a LARGE full prompt held in its own `PromptStore`, so we can observe exactly
which full prompts are loaded.
"""
from __future__ import annotations

import json
import re

from app.skills.base import Skill, SkillContext, SkillMetadata
from app.skills.registry import SkillRegistry
from app.utils.prompts import PromptStore

NOUNS = ["invoice", "weather", "calendar", "currency", "recipe", "flight", "hotel", "stock", "crypto",
         "playlist", "podcast", "contract", "resume", "ticket", "shipment", "patent", "lecture", "budget",
         "insurance", "mortgage", "horoscope", "marathon", "vaccine", "satellite", "bicycle"]
VERBS = ["analyze", "forecast", "schedule", "compare", "validate", "archive", "estimate", "monitor"]
MAX_SYNTHETIC_SKILLS = len(NOUNS) * len(VERBS)
FULL_PROMPT_REPEAT = 80          # each synthetic full prompt is ~2,000 characters
FALLBACK_ID = "chat_fallback"


def _prompt_source(name: str) -> str:
    return f"ROLE: {name}\nYou are the detailed skill {name}. " + "Follow these long instructions carefully. " * FULL_PROMPT_REPEAT


def build_synthetic_registry(n: int, store: PromptStore | None = None) -> tuple[SkillRegistry, PromptStore]:
    """``n`` compact synthetic skills plus one fallback skill, backed by ``store``."""
    if not 1 <= n <= MAX_SYNTHETIC_SKILLS:
        raise ValueError(f"n must be between 1 and {MAX_SYNTHETIC_SKILLS}")
    store = store or PromptStore(_prompt_source)
    registry = SkillRegistry()

    def handler_for(skill_id: str):
        def handler(ctx: SkillContext) -> str:
            store.load(skill_id)                    # the full prompt is loaded only when executing
            return f"handled by {skill_id}"
        return handler

    for index in range(n):
        noun, verb = NOUNS[index % len(NOUNS)], VERBS[(index // len(NOUNS)) % len(VERBS)]
        skill_id = f"{noun}_{verb}"
        registry.register(Skill(SkillMetadata(
            id=skill_id, name=f"{verb.title()} {noun.title()}",
            description=f"Will {verb} the user's {noun} information and return the findings.",
            input_types=["text"], operations=[verb],
            routing_examples=[f"Please {verb} my {noun} data"],
            keywords=[rf"\b{noun}\b", rf"\b{verb}"],
            routing_hint=f"Only for {noun} tasks.",
        ), handler_for(skill_id)))
    registry.register(Skill(SkillMetadata(
        id=FALLBACK_ID, name="Chat", description="Greetings and general conversation questions.",
        input_types=["text"], operations=["converse"], routing_examples=["Hello"], is_fallback=True,
    ), handler_for(FALLBACK_ID)))
    return registry, store


class StubRouterLLM:
    """Deterministic stand-in for the LLM (NOT a model): picks the candidate whose id words appear
    in the prompt. It lets the simulation exercise routing/validation/execution without an API
    key; it says nothing about real-model accuracy."""

    _CANDIDATE = re.compile(r"- id=(\w+)")
    _PROMPT = re.compile(r"<user_prompt>\n(.*?)\n</user_prompt>", re.DOTALL)

    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def complete(self, system: str, user: str) -> str:
        if "ROLE: shortlister" in system:
            return json.dumps({"candidates": []})
        self.calls.append((system, user))
        prompt = (self._PROMPT.search(user) or re.search(r"(.*)", user)).group(1).lower()
        ids = self._CANDIDATE.findall(system)
        chosen = next((i for i in ids if all(part in prompt for part in i.split("_"))), ids[0])
        return json.dumps({
            "selected_skills": [chosen], "depends_on_previous": False, "detected_language": "en",
            "confidence": 0.9, "clarification_required": False, "clarification_question": None,
            "unsupported_request": False, "unsupported_reason": None, "reasoning_summary": "stub",
        })
