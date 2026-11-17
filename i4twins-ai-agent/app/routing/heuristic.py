"""Deterministic keyword router: fallback when LLM output cannot be validated, and a baseline.

Uses only skill metadata (keywords, flags), so it needs no per-skill code either.
"""
from __future__ import annotations

import re

from app.schemas.routing import MAX_SKILLS_PER_REQUEST, RoutingDecision
from app.skills.base import SkillMetadata
from app.utils.language import detect_language, normalize_text

_GENERIC_QUESTION = {
    "fa": "منظورتان دقیقاً چیست؟ لطفاً درخواست خود را کامل‌تر بنویسید.",
    "en": "Could you clarify what you need? Please describe your request in a bit more detail.",
}
MIN_CONTENT_WORDS = 3   # fewer leftover words than this -> the request has no text to work on


def fallback_language(prompt: str) -> str:
    detected = detect_language(prompt)
    return detected if detected in ("fa", "en", "ar") else "en"


def clarification_text(language: str, meta: SkillMetadata | None = None) -> str:
    lang = "fa" if language in ("fa", "ar") else "en"
    if meta is not None and meta.missing_input_question:
        return meta.missing_input_question.get(lang) or meta.missing_input_question["en"]
    return _GENERIC_QUESTION[lang]


def _first_match(meta: SkillMetadata, text: str) -> int | None:
    positions = [m.start() for pattern in meta.keywords if (m := re.search(pattern, text))]
    return min(positions) if positions else None


def heuristic_route(prompt: str, candidates: list[SkillMetadata]) -> RoutingDecision:
    """Pick up to two skills by keyword position; chain them when both accept previous output."""
    text = normalize_text(prompt).lower()
    language = fallback_language(prompt)
    hits = [(pos, meta) for meta in candidates
            if not meta.is_fallback and (pos := _first_match(meta, text)) is not None]
    hits.sort(key=lambda pair: (pair[0], pair[1].id))
    skills = [meta for _, meta in hits][:MAX_SKILLS_PER_REQUEST]
    if not skills:
        fallback = next((m for m in candidates if m.is_fallback), None)
        if fallback is None:
            return RoutingDecision(selected_skills=[], detected_language=language, confidence=0.5,
                                   unsupported_request=True, unsupported_reason="No skill matches this request.",
                                   reasoning_summary="No keyword matched and no fallback skill exists.")
        return RoutingDecision(selected_skills=[fallback.id], detected_language=language, confidence=0.5,
                               reasoning_summary="No skill keyword found; using the fallback skill.")
    if len(skills) == 1 and skills[0].requires_content:
        leftover = text
        for pattern in skills[0].keywords:
            leftover = re.sub(pattern, " ", leftover)
        if len(re.findall(r"\w+", leftover)) < MIN_CONTENT_WORDS:
            return RoutingDecision(
                selected_skills=[skills[0].id], detected_language=language, confidence=0.5,
                clarification_required=True, clarification_question=clarification_text(language, skills[0]),
                reasoning_summary="Keyword match, but the request has no text to process.",
            )
    chained = len(skills) == 2 and skills[1].accepts_previous_output and skills[0].accepts_previous_output
    return RoutingDecision(selected_skills=[m.id for m in skills], depends_on_previous=chained,
                           detected_language=language, confidence=0.5,
                           reasoning_summary="Keyword-based fallback routing.")
