import pytest

from app.routing.discovery import MAX_CANDIDATES
from evaluation.scalability import render_markdown, simulate
from evaluation.synthetic_registry import MAX_SYNTHETIC_SKILLS, build_synthetic_registry


@pytest.fixture(scope="module")
def results():
    return {n: simulate(n, queries=10) for n in (10, 100)}


def test_context_never_loads_unselected_prompts(results):
    for r in results.values():
        assert r["any_unselected_prompt_accessed"] is False
        assert r["max_prompts_loaded_before_execution"] == 0
        assert r["avg_prompts_loaded_after_execution"] == r["avg_selected"] == 1.0


def test_candidate_count_is_bounded_by_k_not_by_registry_size(results):
    for r in results.values():
        assert r["avg_candidates"] <= MAX_CANDIDATES + 1


def test_routing_context_stays_flat_as_the_registry_grows(results):
    small, large = results[10]["avg_routing_context_chars"], results[100]["avg_routing_context_chars"]
    assert large < small * 1.3                                       # 10x more skills, ~same context
    assert large < results[100]["naive_all_prompts_chars"] / 20      # versus injecting everything


def test_relevant_skill_is_found_in_the_shortlist(results):
    assert all(r["target_in_shortlist_rate"] == 1.0 for r in results.values())


def test_markdown_report_lists_the_measured_columns(results):
    text = render_markdown(list(results.values()))
    assert "Registered" in text and "Unselected prompt accessed" in text and "approximation" in text


def test_synthetic_registry_is_bounded_and_separate_from_the_app():
    with pytest.raises(ValueError):
        build_synthetic_registry(MAX_SYNTHETIC_SKILLS + 1)
    from app.skills import build_default_registry
    assert len(build_default_registry()) == 4                         # synthetic skills never leak into the app
