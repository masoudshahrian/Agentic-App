from app.graph import build_graph
from app.main import run_request
from app.skills import build_default_registry
from app.skills.registry import SkillRegistry
from tests.conftest import FakeLLM, route_json


def test_unsupported_request_returns_a_clear_error_and_runs_no_skill(make_graph):
    graph, llm = make_graph(router=route_json([], unsupported="Booking flights requires an external action."))
    state = run_request(graph, "Book me a flight to Tehran tomorrow")
    assert state.unsupported_request and not state.skill_results
    assert "not supported" in state.final_response and "Booking flights" in state.final_response
    assert "Summarizer" in state.final_response and "Calculator" in state.final_response   # tells what IS supported
    assert llm.roles() == ["router"]                                                        # nothing executed


def test_unsupported_answer_is_persian_for_persian_prompts(make_graph):
    graph, _ = make_graph(router=route_json([], lang="fa", unsupported="رزرو بلیت ممکن نیست"))
    state = run_request(graph, "برای من بلیت هواپیما رزرو کن")
    assert "پشتیبانی نمی‌شود" in state.final_response


def test_greeting_and_general_questions_use_general_chat_not_an_error(make_graph):
    graph, _ = make_graph(router=[route_json(["general_chat"]), route_json(["general_chat"], lang="fa")],
                          general_chat="Hi!")
    assert run_request(graph, "Hello, how are you?").final_response == "Hi!"
    assert not run_request(graph, "سلام، حالت چطور است؟").unsupported_request


def test_ambiguous_request_triggers_clarification_not_a_guess(make_graph):
    graph, llm = make_graph(router=route_json(["translator"], confidence=0.6, clarification="Which text?"),
                            translator="must not run")
    state = run_request(graph, "Translate this.")
    assert state.final_response == "Which text?" and llm.roles() == ["router"]


def test_without_a_fallback_skill_the_keyword_router_reports_unsupported():
    registry = SkillRegistry([s for s in build_default_registry() if not s.metadata.is_fallback])
    graph = build_graph(FakeLLM(router="garbage"), registry)
    state = run_request(graph, "Book me a flight")
    assert state.unsupported_request and state.routing_source == "fallback"
    assert "not supported" in state.final_response


def test_unknown_skill_id_from_the_llm_is_never_executed(make_graph):
    graph, llm = make_graph(router=route_json(["poet"]), calculator='{"expression": "245*36"}')
    state = run_request(graph, "What is 245 * 36?")
    assert state.routing_source == "fallback" and "poet" not in state.skill_results
    assert state.selected_skills == ["calculator"]


def test_at_most_two_skills_are_ever_executed(make_graph):
    graph, llm = make_graph(router=route_json(["summarizer", "translator", "calculator"]),
                            summarizer="s", translator="t", calculator='{"expression": "1+1"}')
    state = run_request(graph, "Summarize, translate and compute 1+1: some words in this text here")
    assert len(state.selected_skills) <= 2 and len(state.skill_results) <= 2
