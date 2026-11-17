import pytest

from app.config import ConfigError, load_settings
from app.graph import AgentState, build_graph
from app.llm import LLMError
from app.main import run_request
from app.skills import build_default_registry
from tests.conftest import FakeLLM, llm_error, route_json


def test_graph_has_constant_node_set():
    nodes = set(build_graph(FakeLLM()).get_graph().nodes) - {"__start__", "__end__"}
    assert nodes == {"discover", "router", "execute_skill", "aggregator"}   # independent of skill count


def test_exactly_four_registered_skills():
    registry = build_default_registry()
    assert sorted(registry.ids()) == ["calculator", "general_chat", "summarizer", "translator"]


def test_general_chat_flow(make_graph):
    graph, llm = make_graph(router=route_json(["general_chat"]), general_chat="I'm fine, thanks!")
    state = run_request(graph, "Hello, how are you?")
    assert isinstance(state, AgentState)
    assert state.final_response == "I'm fine, thanks!" and state.selected_skills == ["general_chat"]
    assert llm.roles() == ["router", "general_chat"]


def test_calculator_flow_uses_tool_value(make_graph):
    graph, _ = make_graph(router=route_json(["calculator"]), calculator='{"expression": "245*36"}')
    assert run_request(graph, "What is 245 * 36?").final_response == "245*36 = 8820"


def test_clarification_skips_all_skills(make_graph):
    graph, llm = make_graph(router=route_json(["translator"], confidence=0.6,
                                              clarification="Which text should I translate?"),
                            translator="must not run")
    state = run_request(graph, "Translate this.")
    assert state.final_response == "Which text should I translate?"
    assert state.clarification_required and llm.roles() == ["router"]


def test_original_prompt_is_preserved(make_graph):
    prompt = "  حاصل ۲۵ ضربدر ۴۸ چیست؟  "
    graph, _ = make_graph(router=route_json(["calculator"], lang="fa"), calculator='{"expression": "25*48"}')
    state = run_request(graph, prompt)
    assert state.original_prompt == prompt and state.normalized_prompt == "حاصل 25 ضربدر 48 چیست?"


def test_each_request_starts_with_a_fresh_state(make_graph):
    graph, llm = make_graph(router=[route_json(["general_chat"]), route_json(["calculator"])],
                            general_chat="hi", calculator='{"expression": "2+2"}')
    first = run_request(graph, "Hello")
    second = run_request(graph, "2+2")
    assert first.skill_results == {"general_chat": "hi"}
    assert second.skill_results == {"calculator": "2+2 = 4"}          # nothing leaked from request 1
    assert "Hello" not in llm.calls[-1][1] and "Hello" not in llm.calls[-2][1]


def test_provider_failure_in_router_is_reported(make_graph):
    graph, llm = make_graph(router=llm_error())
    state = run_request(graph, "Hello")
    assert "Sorry" in state.final_response and "rate limit" in state.final_response
    assert llm.roles() == ["router"]


def test_provider_failure_in_skill_is_reported(make_graph):
    graph, _ = make_graph(router=route_json(["general_chat"]), general_chat=LLMError("network error"))
    state = run_request(graph, "Hello")
    assert "network error" in state.final_response and state.errors


def test_router_fallback_still_answers(make_graph):
    graph, _ = make_graph(router="garbage", calculator='{"expression": "245*36"}')
    state = run_request(graph, "What is 245 * 36?")
    assert state.routing_source == "fallback" and state.final_response == "245*36 = 8820"
    assert state.routing_notes


def test_empty_prompt(make_graph):
    graph, llm = make_graph(router="unused")
    state = run_request(graph, "   ")
    assert state.final_response == "Please type a request." and not llm.calls


# ------------------------------------------------------------------ configuration
def test_missing_api_key_raises_config_error():
    with pytest.raises(ConfigError, match="OPENROUTER_API_KEY"):
        load_settings({})


def test_placeholder_key_is_rejected():
    with pytest.raises(ConfigError):
        load_settings({"OPENROUTER_API_KEY": "your_openrouter_api_key"})


def test_unsupported_provider_rejected():
    with pytest.raises(ConfigError, match="not supported"):
        load_settings({"LLM_PROVIDER": "openai", "OPENROUTER_API_KEY": "k"})


def test_invalid_number_rejected():
    with pytest.raises(ConfigError, match="LLM_TEMPERATURE"):
        load_settings({"OPENROUTER_API_KEY": "k", "LLM_TEMPERATURE": "hot"})


def test_settings_from_env_and_key_never_in_repr():
    s = load_settings({"OPENROUTER_API_KEY": "sk-secret", "LLM_MODEL": "some/model:free"})
    assert s.model == "some/model:free" and "sk-secret" not in repr(s) and "sk-secret" not in str(s)
    assert load_settings({"OPENROUTER_API_KEY": "k"}).model == "google/gemma-4-31b-it:free"
