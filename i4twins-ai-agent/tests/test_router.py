import pytest
from pydantic import ValidationError

from app.routing.heuristic import heuristic_route
from app.routing.router import CONFIDENCE_THRESHOLD, build_system_prompt, render_candidate, route_prompt
from app.schemas.routing import RoutingDecision
from app.skills import build_default_registry
from app.utils.jsonio import StructuredOutputError, parse_model
from app.utils.prompts import load_prompt
from tests.conftest import FakeLLM, llm_error, route_json

BASE = dict(detected_language="en", confidence=0.9)
METAS = build_default_registry().metadata()
BY_ID = {m.id: m for m in METAS}
TEMPLATE = load_prompt("router")


# ------------------------------------------------------------------ schema
def test_valid_decision():
    d = RoutingDecision(selected_skills=["summarizer", "translator"], depends_on_previous=True, **BASE)
    assert d.selected_skills == ["summarizer", "translator"]
    d.check_against(BY_ID)


def test_skill_ids_are_case_insensitive():
    assert RoutingDecision(selected_skills=[" Calculator "], **BASE).selected_skills == ["calculator"]


@pytest.mark.parametrize("bad", [
    dict(selected_skills=[]),                                          # none selected, not unsupported
    dict(selected_skills=["summarizer", "summarizer"]),                # duplicate
    dict(selected_skills=["summarizer", "translator", "calculator"]),  # more than two
    dict(selected_skills=["translator"], depends_on_previous=True),    # dependency needs two
    dict(selected_skills=["translator"], confidence=1.5),              # out of range
    dict(selected_skills=["translator"], confidence=-0.1),
    dict(selected_skills=["translator"], detected_language="Persian"),
    dict(selected_skills=["translator"], clarification_required=True),  # no question
    dict(selected_skills=["translator"], clarification_question="Which text?"),
    dict(selected_skills="translator"),                                 # wrong type
    dict(selected_skills=["translator"], unsupported_request=True, unsupported_reason="x"),  # both
    dict(selected_skills=[], unsupported_request=True),                 # reason missing
    dict(selected_skills=["translator"], unsupported_reason="x"),       # reason without flag
])
def test_invalid_decisions_rejected(bad):
    with pytest.raises(ValidationError):
        RoutingDecision(**{**BASE, **bad})


def test_unsupported_decision_is_valid_without_skills():
    d = RoutingDecision(selected_skills=[], unsupported_request=True, unsupported_reason="needs booking", **BASE)
    assert d.unsupported_request and not d.selected_skills


def test_blank_question_treated_as_none():
    d = RoutingDecision(selected_skills=["translator"], clarification_question="  ", **BASE)
    assert d.clarification_question is None


def test_unknown_skill_id_rejected_against_registry():
    d = RoutingDecision(selected_skills=["poet"], **BASE)
    with pytest.raises(ValueError, match="unknown or non-shortlisted"):
        d.check_against(BY_ID)


def test_fallback_skill_cannot_be_combined():
    d = RoutingDecision(selected_skills=["general_chat", "translator"], **BASE)
    with pytest.raises(ValueError, match="fallback"):
        d.check_against(BY_ID)


def test_parse_model_reports_validation_problems():
    with pytest.raises(StructuredOutputError, match="selected_skills"):
        parse_model(route_json(["a", "b", "c"]), RoutingDecision)


# ------------------------------------------------------------------ route_prompt (stage 2)
def test_valid_llm_route():
    llm = FakeLLM(router=route_json(["calculator"]))
    result = route_prompt(llm, "What is 245 * 36?", TEMPLATE, METAS)
    assert result.source == "llm" and result.decision.selected_skills == ["calculator"]
    assert result.context_chars == len(llm.system_for("router")) + len(llm.user_for("router"))


def test_router_prompt_contains_only_compact_metadata():
    llm = FakeLLM(router=route_json(["calculator"]))
    route_prompt(llm, "What is 245 * 36?", TEMPLATE, METAS)
    system = llm.system_for("router")
    assert all(f"id={m.id}" in system for m in METAS)
    for role in ("summarizer", "translator", "calculator", "general_chat"):
        assert load_prompt(role) not in system      # never a full skill prompt


def test_code_fenced_json_is_accepted():
    llm = FakeLLM(router="```json\n" + route_json(["general_chat"]) + "\n```")
    assert route_prompt(llm, "Hello", TEMPLATE, METAS).source == "llm"


def test_malformed_output_retries_once_then_succeeds():
    llm = FakeLLM(router=["not json at all", route_json(["translator"])])
    result = route_prompt(llm, "Translate hello to Persian", TEMPLATE, METAS)
    assert result.source == "llm" and len(llm.calls) == 2
    assert "previous reply was invalid" in llm.calls[1][1]


def test_unknown_skill_id_triggers_retry_and_then_fallback():
    llm = FakeLLM(router=route_json(["poet"]))
    result = route_prompt(llm, "Summarize this long text please: lots of words here and there", TEMPLATE, METAS)
    assert result.source == "fallback" and len(llm.calls) == 2
    assert result.decision.selected_skills == ["summarizer"]
    assert any("unknown or non-shortlisted" in e for e in result.errors)


def test_more_than_two_skills_is_never_accepted():
    llm = FakeLLM(router=route_json(["summarizer", "translator", "calculator"]))
    result = route_prompt(llm, "Summarize this long text please: lots of words here and there", TEMPLATE, METAS)
    assert result.source == "fallback"


def test_provider_failure_returns_no_decision():
    result = route_prompt(FakeLLM(router=llm_error()), "Hello", TEMPLATE, METAS)
    assert result.decision is None and "router failed" in result.errors[-1]


def test_empty_prompt_never_calls_the_llm():
    llm = FakeLLM(router="unused")
    result = route_prompt(llm, "   ", TEMPLATE, METAS)
    assert not llm.calls and result.decision.clarification_required


def test_low_confidence_triggers_clarification():
    llm = FakeLLM(router=route_json(["translator"], confidence=CONFIDENCE_THRESHOLD - 0.1))
    decision = route_prompt(llm, "hmm do the thing", TEMPLATE, METAS).decision
    assert decision.clarification_required and decision.clarification_question


def test_persian_script_overrides_wrong_language_code():
    llm = FakeLLM(router=route_json(["general_chat"], lang="en"))
    assert route_prompt(llm, "سلام، حالت چطور است؟", TEMPLATE, METAS).decision.detected_language == "fa"


def test_math_symbols_do_not_make_prompt_english():
    llm = FakeLLM(router=route_json(["calculator"], lang="fa"))
    assert route_prompt(llm, "۲۵*۴۸", TEMPLATE, METAS).decision.detected_language == "fa"


def test_dependency_downgraded_when_second_skill_cannot_chain():
    llm = FakeLLM(router=route_json(["translator", "calculator"], dependent=True))
    result = route_prompt(llm, "Translate hi to French and compute 2+2", TEMPLATE, METAS)
    assert result.decision.depends_on_previous is False
    assert any("cannot take previous output" in e for e in result.errors)


def test_unsupported_decision_passes_through():
    llm = FakeLLM(router=route_json([], unsupported="Booking flights is not possible"))
    decision = route_prompt(llm, "Book me a flight to Tehran", TEMPLATE, METAS).decision
    assert decision.unsupported_request and decision.selected_skills == []


def test_render_candidate_is_compact():
    for meta in METAS:
        assert len(render_candidate(meta)) < 700
    assert "<<" not in build_system_prompt(TEMPLATE, METAS)


# ------------------------------------------------------------------ deterministic fallback
@pytest.mark.parametrize("prompt, skills", [
    ("Summarize this article: The council met on Tuesday and voted on the new budget.", ["summarizer"]),
    ("Translate this paragraph into Persian: The weather is nice today.", ["translator"]),
    ("What is 245 * 36?", ["calculator"]),
    ("Hello, how are you?", ["general_chat"]),
    ("این متن را خلاصه کن: شهرداری امروز بودجه جدید را تصویب کرد و اجرای آن از ماه آینده آغاز می‌شود.", ["summarizer"]),
    ("حاصل ۲۵ ضربدر ۴۸ چیست؟", ["calculator"]),
    ("سلام، حالت چطور است؟", ["general_chat"]),
    ("Summarize this text and translate the summary into Persian: Some long text goes here.",
     ["summarizer", "translator"]),
])
def test_heuristic_routes(prompt, skills):
    assert heuristic_route(prompt, METAS).selected_skills == skills


def test_heuristic_chains_two_chainable_skills():
    d = heuristic_route("Summarize this text and translate the summary into Persian: abc def ghi", METAS)
    assert d.depends_on_previous


def test_heuristic_does_not_chain_non_chainable():
    d = heuristic_route("Translate 'good morning' into French and calculate 25 * 48.", METAS)
    assert d.selected_skills == ["translator", "calculator"] and not d.depends_on_previous


@pytest.mark.parametrize("prompt", ["Translate this.", "ترجمه کن", "Summarize"])
def test_heuristic_asks_when_there_is_no_text(prompt):
    assert heuristic_route(prompt, METAS).clarification_required


def test_heuristic_without_fallback_skill_reports_unsupported():
    no_chat = [m for m in METAS if not m.is_fallback]
    assert heuristic_route("Book me a flight", no_chat).unsupported_request
