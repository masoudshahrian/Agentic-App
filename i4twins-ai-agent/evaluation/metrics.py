"""Routing metrics. Pure functions over (expected, predicted) records."""
from __future__ import annotations

from dataclasses import dataclass

SKILLS = ("summarizer", "translator", "calculator", "general_chat")  # the registered skills under test


@dataclass(frozen=True)
class Record:
    expected_skills: tuple[str, ...]
    predicted_skills: tuple[str, ...]
    expected_clarification: bool
    predicted_clarification: bool
    language: str = "en"
    expected_unsupported: bool = False
    predicted_unsupported: bool = False


def _ratio(num: int, den: int) -> float | None:
    return None if den == 0 else num / den


def compute_metrics(records: list[Record]) -> dict:
    """Exact skill-set accuracy, per-skill P/R/F1, multi-skill, clarification, Persian accuracy."""
    exact = [set(r.expected_skills) == set(r.predicted_skills) for r in records]
    per_skill = {}
    for skill in SKILLS:
        tp = sum(skill in r.expected_skills and skill in r.predicted_skills for r in records)
        fp = sum(skill not in r.expected_skills and skill in r.predicted_skills for r in records)
        fn = sum(skill in r.expected_skills and skill not in r.predicted_skills for r in records)
        precision, recall = _ratio(tp, tp + fp), _ratio(tp, tp + fn)
        f1 = None if precision is None or recall is None or precision + recall == 0 else (
            2 * precision * recall / (precision + recall))
        per_skill[skill] = {"precision": precision, "recall": recall, "f1": f1, "support": tp + fn}
    multi = [e for r, e in zip(records, exact) if len(r.expected_skills) == 2]
    persian = [e for r, e in zip(records, exact) if r.language == "fa"]
    clarification = [r.expected_clarification == r.predicted_clarification for r in records]
    unsupported = [r.expected_unsupported == r.predicted_unsupported for r in records]
    return {
        "n": len(records),
        "exact_skill_set_accuracy": _ratio(sum(exact), len(exact)),
        "per_skill": per_skill,
        "multi_skill_detection_accuracy": _ratio(sum(multi), len(multi)),
        "multi_skill_n": len(multi),
        "clarification_accuracy": _ratio(sum(clarification), len(clarification)),
        "unsupported_accuracy": _ratio(sum(unsupported), len(unsupported)),
        "persian_routing_accuracy": _ratio(sum(persian), len(persian)),
        "persian_n": len(persian),
    }
