"""Builds the LangGraph StateGraph (constant size, whatever the number of skills).

START -> discover -> router -> execute_skill (xN, parallel or chained) -> aggregator -> END

- discover       stage 1: shortlist candidate skills from compact metadata (no full prompts)
- router         stage 2: LLM chooses 1-2 skills among the candidates only; validated
- execute_skill  stage 3: runs one selected skill; invoked via `Send` once per selected skill
- aggregator     builds the final answer (clarification / unsupported / results / errors)
"""
from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from app.graph.edges import AGGREGATOR, EXECUTE, route_after_router, route_after_skill
from app.graph.nodes import (make_aggregator_node, make_discover_node, make_execute_node,
                             make_router_node)
from app.graph.state import AgentState, SkillTask
from app.llm import LLM
from app.skills import build_default_registry
from app.skills.registry import SkillRegistry
from app.utils.prompts import load_prompt


def build_graph(llm: LLM, registry: SkillRegistry | None = None, router_prompt: str | None = None):
    """Compile the agent graph. ``router_prompt`` overrides the router template (A/B evaluation)."""
    registry = build_default_registry() if registry is None else registry
    if len(registry) == 0:
        raise ValueError("the skill registry is empty")
    graph = StateGraph(AgentState)
    graph.add_node("discover", make_discover_node(registry, llm))
    graph.add_node("router", make_router_node(registry, llm, router_prompt or load_prompt("router")))
    graph.add_node(EXECUTE, make_execute_node(registry, llm), input_schema=SkillTask)
    graph.add_node(AGGREGATOR, make_aggregator_node(registry))

    graph.add_edge(START, "discover")
    graph.add_edge("discover", "router")
    graph.add_conditional_edges("router", route_after_router, [EXECUTE, AGGREGATOR])
    graph.add_conditional_edges(EXECUTE, route_after_skill, [EXECUTE, AGGREGATOR])
    graph.add_edge(AGGREGATOR, END)
    return graph.compile()
