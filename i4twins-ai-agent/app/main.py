"""Entry points for running one independent request through the graph."""
from __future__ import annotations

from dataclasses import replace

from app.config import load_settings
from app.graph import AgentState, build_graph
from app.llm import LLM, OpenRouterLLM


def create_llm(model: str | None = None) -> LLM:
    """Build the configured LLM client (raises ConfigError when the key is missing).

    ``model`` overrides ``LLM_MODEL`` for this client only.
    """
    settings = load_settings()
    return OpenRouterLLM(replace(settings, model=model) if model else settings)


def run_request(graph, prompt: str) -> AgentState:
    """Run one request with a fresh state: nothing is carried over between calls."""
    result = graph.invoke({"original_prompt": prompt})
    return result if isinstance(result, AgentState) else AgentState.model_validate(result)
