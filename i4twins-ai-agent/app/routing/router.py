"""Stage 2 - focused skill selection over the shortlisted candidates only."""
from __future__ import annotations

from dataclasses import dataclass, field

from app.llm import LLM, LLMError
from app.routing.heuristic import clarification_text, heuristic_route
from app.schemas.routing import MAX_SKILLS_PER_REQUEST, RoutingDecision
from app.skills.base import SkillMetadata
from app.utils.jsonio import StructuredOutputError, parse_model
from app.utils.language import detect_language

CONFIDENCE_THRESHOLD = 0.4   # below this the router is not trusted -> ask for clarification


@dataclass
class RouteResult:
    decision: RoutingDecision | None
    source: str                                       # "llm" | "fallback" | "none"
    errors: list[str] = field(default_factory=list)   # routing notes / failures
    context_chars: int = 0                            # size of the stage-2 LLM input (system + user)


def render_candidate(meta: SkillMetadata) -> str:
    """One compact line per candidate: this is the ONLY skill information the router receives."""
    tags = [t for t, on in (("fallback", meta.is_fallback), ("chainable", meta.accepts_previous_output)) if on]
    parts = [f"- id={meta.id} | {meta.name}: {meta.description}",
             f"operations: {', '.join(meta.operations)}", f"input: {', '.join(meta.input_types)}"]
    if meta.routing_hint:
        parts.append(f"hint: {meta.routing_hint}")
    parts.append("examples: " + " ; ".join(f'"{e}"' for e in meta.routing_examples))
    if tags:
        parts.append("[" + ", ".join(tags) + "]")
    return " | ".join(parts)


def build_system_prompt(template: str, candidates: list[SkillMetadata]) -> str:
    return (template.replace("<<CANDIDATES>>", "\n".join(render_candidate(m) for m in candidates))
                    .replace("<<MAX_SKILLS>>", str(MAX_SKILLS_PER_REQUEST)))


def _parse_and_validate(raw: str, by_id: dict[str, SkillMetadata]) -> RoutingDecision:
    decision = parse_model(raw, RoutingDecision)
    try:
        decision.check_against(by_id)
    except ValueError as exc:
        raise StructuredOutputError(str(exc)) from None
    return decision


def apply_policy(decision: RoutingDecision, prompt: str,
                 by_id: dict[str, SkillMetadata]) -> tuple[RoutingDecision, list[str]]:
    """Post-validation policy. Returns the (possibly adjusted) decision and notes."""
    updates: dict[str, object] = {}
    notes: list[str] = []
    script = detect_language(prompt)
    if script in ("fa", "ar") and decision.detected_language not in ("fa", "ar"):
        updates["detected_language"] = script
    if decision.depends_on_previous and not by_id[decision.selected_skills[1]].accepts_previous_output:
        updates["depends_on_previous"] = False   # the second skill cannot consume output -> parallel
        notes.append(f"'{decision.selected_skills[1]}' cannot take previous output; running in parallel")
    if (not decision.unsupported_request and not decision.clarification_required
            and decision.confidence < CONFIDENCE_THRESHOLD):
        language = str(updates.get("detected_language", decision.detected_language))
        updates.update(clarification_required=True, clarification_question=clarification_text(language))
    return (decision.model_copy(update=updates) if updates else decision), notes


def route_prompt(llm: LLM, prompt: str, template: str, candidates: list[SkillMetadata]) -> RouteResult:
    """Ask the LLM to choose among ``candidates``; validate; retry once; then fall back."""
    by_id = {m.id: m for m in candidates}
    if not prompt.strip():
        decision = RoutingDecision(
            selected_skills=[], detected_language="en", confidence=1.0,
            clarification_required=True, clarification_question="Please type a request.",
            reasoning_summary="Empty prompt.",
        )
        return RouteResult(decision, "none")

    system = build_system_prompt(template, candidates)
    user = f"<user_prompt>\n{prompt}\n</user_prompt>\nScript-based language hint: {detect_language(prompt)}"
    errors: list[str] = []
    context_chars = 0
    for attempt in range(2):  # first try + one corrective retry
        message = user if attempt == 0 else (
            f"{user}\n\nYour previous reply was invalid ({errors[-1]}). Reply with ONLY the corrected JSON object."
        )
        context_chars += len(system) + len(message)
        try:
            decision = _parse_and_validate(llm.complete(system, message), by_id)
        except StructuredOutputError as exc:
            errors.append(f"router output invalid: {exc}")
            continue
        except LLMError as exc:
            return RouteResult(None, "none", [*errors, f"router failed: {exc}"], context_chars)
        decision, notes = apply_policy(decision, prompt, by_id)
        return RouteResult(decision, "llm", [*errors, *notes], context_chars)
    errors.append("router output invalid twice; using deterministic fallback routing")
    decision, notes = apply_policy(heuristic_route(prompt, candidates), prompt, by_id)
    return RouteResult(decision, "fallback", [*errors, *notes], context_chars)
