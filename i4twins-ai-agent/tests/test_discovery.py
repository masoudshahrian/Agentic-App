import json

import pytest

from app.graph import build_graph
from app.main import run_request
from app.routing.discovery import FULL_LISTING_LIMIT, MAX_CANDIDATES, discover, render_index, score
from app.skills import build_default_registry
from app.utils.prompts import default_store, load_prompt
from evaluation.synthetic_registry import FALLBACK_ID, StubRouterLLM, build_synthetic_registry
from tests.conftest import FakeLLM, llm_error, route_json


def test_small_registry_lists_every_skill():
    result = discover(build_default_registry(), "anything at all")
    assert result.strategy == "all" and len(result.candidates) == 4 == result.registered


def test_large_registry_is_narrowed_lexically():
    registry, _ = build_synthetic_registry(100)
    result = discover(registry, "Please forecast my weather data now")
    assert result.strategy == "lexical" and len(result.candidates) <= MAX_CANDIDATES + 1
    assert "weather_forecast" in result.candidate_ids          # the relevant skill is shortlisted
    assert FALLBACK_ID in result.candidate_ids                  # fallback is always available
    assert result.registered == 101


def test_two_skill_request_keeps_both_skills_in_the_shortlist():
    registry, _ = build_synthetic_registry(100)
    result = discover(registry, "Please forecast the weather and also schedule my calendar")
    assert {"weather_forecast", "calendar_schedule"} <= set(result.candidate_ids)


def test_persian_and_english_scoring_on_real_skills():
    metas = {m.id: m for m in build_default_registry().metadata()}
    assert score("حاصل ۲۵ ضربدر ۴۸ چیست؟", metas["calculator"]) > score("حاصل ۲۵ ضربدر ۴۸ چیست؟", metas["translator"])
    assert score("این متن را خلاصه کن", metas["summarizer"]) > 0
    assert score("Translate this into French", metas["translator"]) > score("Translate this into French", metas["calculator"])


def test_no_lexical_match_uses_llm_shortlist_over_a_compact_index():
    registry, _ = build_synthetic_registry(100)
    llm = FakeLLM(shortlister=json.dumps({"candidates": ["hotel_compare", "ghost_skill", "hotel_compare"]}))
    result = discover(registry, "zzz qqq", llm)
    assert result.strategy == "llm_shortlist"
    assert result.candidate_ids == ["hotel_compare", FALLBACK_ID]      # unknown ids dropped, deduplicated
    index = llm.user_for("shortlister")
    assert "Follow these long instructions" not in index              # compact index, no full prompts
    assert len(index) < len(render_index(registry.metadata())) + 200


@pytest.mark.parametrize("reply", ["garbage", llm_error()])
def test_failed_llm_shortlist_degrades_to_fallback_only(reply):
    registry, _ = build_synthetic_registry(100)
    result = discover(registry, "zzz qqq", FakeLLM(shortlister=reply))
    assert result.strategy == "fallback_only" and result.candidate_ids == [FALLBACK_ID] and result.notes


def test_no_match_and_no_llm_is_fallback_only():
    registry, _ = build_synthetic_registry(100)
    assert discover(registry, "zzz qqq").strategy == "fallback_only"


def test_threshold_constants_are_consistent():
    assert FULL_LISTING_LIMIT >= 4 > 0 and MAX_CANDIDATES >= 2


# ------------------------------------------------------------------ routing + execution from a larger registry
def test_selecting_from_a_larger_registry_end_to_end():
    registry, store = build_synthetic_registry(100)
    graph = build_graph(StubRouterLLM(), registry)
    state = run_request(graph, "Please compare my mortgage data now")
    assert state.selected_skills == ["mortgage_compare"]
    assert state.final_response == "handled by mortgage_compare"
    assert state.discovery_strategy == "lexical" and len(state.candidate_skills) <= MAX_CANDIDATES + 1
    assert state.registered_skill_count == 101


def test_unselected_full_prompts_are_never_loaded():
    registry, store = build_synthetic_registry(100)
    graph = build_graph(StubRouterLLM(), registry)
    store.reset_access_log()
    run_request(graph, "Please compare my mortgage data now")
    assert store.accessed == {"mortgage_compare"}              # only the selected skill's prompt


def test_no_full_prompt_is_loaded_during_discovery_and_routing():
    from app.routing.router import route_prompt
    registry, store = build_synthetic_registry(100)
    store.reset_access_log()
    discovery = discover(registry, "Please compare my mortgage data now")
    route_prompt(StubRouterLLM(), "Please compare my mortgage data now", load_prompt("router"), discovery.candidates)
    assert store.accessed == set()


def test_only_the_selected_real_skill_prompt_is_loaded_and_sent(make_graph):
    default_store.reset_access_log()
    graph, llm = make_graph(router=route_json(["translator"]), translator="Hello")
    run_request(graph, "Translate to English: سلام")
    assert default_store.accessed == {"router", "translator"}
    for other in ("summarizer", "calculator", "general_chat"):
        assert other not in default_store.accessed
        assert load_prompt(other) not in llm.system_for("translator")     # execution sees only its own prompt
    assert llm.roles() == ["router", "translator"]


def test_empty_prompt_on_a_large_registry_makes_no_llm_call():
    registry, _ = build_synthetic_registry(100)
    llm = FakeLLM(shortlister="unused")
    assert discover(registry, "   ", llm).strategy == "fallback_only" and not llm.calls


def test_empty_prompt_on_a_large_registry_without_fallback_asks_for_input():
    from app.skills.registry import SkillRegistry
    registry, _ = build_synthetic_registry(100)
    no_fallback = SkillRegistry([s for s in registry if not s.metadata.is_fallback])
    state = run_request(build_graph(FakeLLM(), no_fallback), "   ")
    assert state.final_response == "Please type a request." and not state.skill_results


def test_empty_registry_is_rejected():
    from app.skills.registry import SkillRegistry
    with pytest.raises(ValueError, match="empty"):
        build_graph(FakeLLM(), SkillRegistry())
