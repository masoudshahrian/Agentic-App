"""Conditional edges. They work on skill ids only: nothing here knows any specific skill."""
from __future__ import annotations

from langgraph.types import Send

from app.graph.state import AgentState, SkillTask

AGGREGATOR = "aggregator"
EXECUTE = "execute_skill"


def _task(state: AgentState, skill_id: str, previous_output: str | None = None) -> Send:
    return Send(EXECUTE, SkillTask(skill_id=skill_id, prompt=state.original_prompt,
                                   previous_output=previous_output, language=state.detected_language))


def route_after_router(state: AgentState) -> list[Send | str]:
    """Clarification / unsupported / failure -> aggregator; else fan out to the selected skills.

    Two independent skills are dispatched together (parallel); a dependent pair starts with
    the first skill only and `route_after_skill` continues the chain.
    """
    if state.clarification_required or state.unsupported_request or not state.selected_skills:
        return [AGGREGATOR]
    if len(state.selected_skills) == 2 and not state.depends_on_previous:
        return [_task(state, skill_id) for skill_id in state.selected_skills]
    return [_task(state, state.selected_skills[0])]


def route_after_skill(state: AgentState) -> Send | str:
    """After a skill: continue a dependent chain with the previous output, or aggregate."""
    if state.depends_on_previous and not state.errors:
        for index, skill_id in enumerate(state.selected_skills):
            if skill_id not in state.skill_results:
                previous = state.skill_results.get(state.selected_skills[index - 1]) if index else None
                return _task(state, skill_id, previous)
    return AGGREGATOR
