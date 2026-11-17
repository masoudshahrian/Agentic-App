"""LangGraph nodes: discover (stage 1), router (stage 2), execute_skill (stage 3), aggregator.

The node set is constant: adding skills to the registry never adds nodes or edges.
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.graph.state import AgentState, SkillTask
from app.llm import LLM, LLMError
from app.routing.discovery import discover
from app.routing.router import route_prompt
from app.skills.base import SkillContext, SkillError
from app.skills.registry import RegistryError, SkillRegistry
from app.utils.language import detect_language, normalize_text

_FAILURE = {"en": "Sorry, I could not complete the request:", "fa": "متأسفم، درخواست انجام نشد:"}
_PARTIAL = {"en": "Note:", "fa": "توجه:"}
_UNSUPPORTED = {
    "en": "Sorry, this request is not supported: {reason}\nI can help with: {skills}.",
    "fa": "متأسفم، این درخواست پشتیبانی نمی‌شود: {reason}\nمن می‌توانم در این موارد کمک کنم: {skills}.",
}

Node = Callable[..., dict[str, Any]]


def make_discover_node(registry: SkillRegistry, llm: LLM) -> Node:
    def discover_node(state: AgentState) -> dict[str, Any]:
        result = discover(registry, state.original_prompt, llm)
        return {
            "normalized_prompt": normalize_text(state.original_prompt),
            "detected_language": detect_language(state.original_prompt),
            "candidate_skills": result.candidate_ids,
            "registered_skill_count": result.registered,
            "discovery_strategy": result.strategy,
            "routing_notes": result.notes,
        }

    return discover_node


def make_router_node(registry: SkillRegistry, llm: LLM, template: str) -> Node:
    def router_node(state: AgentState) -> dict[str, Any]:
        candidates = [registry.get(i).metadata for i in state.candidate_skills]
        result = route_prompt(llm, state.original_prompt, template, candidates)
        if result.decision is None:  # provider failure: nothing can run
            return {"selected_skills": [], "errors": result.errors,
                    "routing_context_chars": result.context_chars}
        d = result.decision
        return {
            "selected_skills": d.selected_skills,
            "depends_on_previous": d.depends_on_previous,
            "detected_language": d.detected_language,
            "routing_confidence": d.confidence,
            "routing_source": result.source,
            "routing_context_chars": result.context_chars,
            "reasoning_summary": d.reasoning_summary,
            "routing_notes": [*state.routing_notes, *result.errors],
            "clarification_required": d.clarification_required,
            "clarification_question": d.clarification_question,
            "unsupported_request": d.unsupported_request,
            "unsupported_reason": d.unsupported_reason,
        }

    return router_node


def make_execute_node(registry: SkillRegistry, llm: LLM) -> Node:
    def execute_skill(task: SkillTask) -> dict[str, Any]:
        """Run ONE selected skill. Only this skill's handler (and prompt) is touched."""
        try:
            skill = registry.get(task.skill_id)
            text = skill.run(SkillContext(llm, task.prompt, task.previous_output, task.language))
        except (LLMError, SkillError, RegistryError) as exc:
            return {"errors": [f"{task.skill_id}: {exc}"]}
        return {"skill_results": {task.skill_id: text}}

    return execute_skill


def make_aggregator_node(registry: SkillRegistry) -> Node:
    def label(skill_id: str, lang: str) -> str:
        labels = registry.get(skill_id).metadata.result_labels
        return labels.get(lang) or labels.get("en") or registry.get(skill_id).metadata.name

    def aggregator_node(state: AgentState) -> dict[str, Any]:
        """Combine skill outputs into the final response (no LLM call)."""
        lang = "fa" if state.detected_language in ("fa", "ar") else "en"
        if state.clarification_required and state.clarification_question:
            return {"final_response": state.clarification_question}
        if state.unsupported_request:
            names = ", ".join(m.name for m in registry.metadata())
            return {"final_response": _UNSUPPORTED[lang].format(reason=state.unsupported_reason, skills=names)}

        ordered = [s for s in state.selected_skills if s in state.skill_results]
        if not ordered:
            problems = "\n".join(f"- {e}" for e in state.errors) or "- no skill produced a result"
            return {"final_response": f"{_FAILURE[lang]}\n{problems}"}

        if len(ordered) == 1 or state.depends_on_previous:
            text = state.skill_results[ordered[-1]]       # chained: the last step is the answer
        else:                                              # independent: labelled sections
            text = "\n\n".join(f"{label(s, lang)}:\n{state.skill_results[s]}" for s in ordered)
        if state.errors:
            text += f"\n\n{_PARTIAL[lang]} " + "; ".join(state.errors)
        return {"final_response": text}

    return aggregator_node
