from app.skills.base import SkillContext
from app.skills import translator
from app.utils.prompts import load_prompt
from tests.conftest import FakeLLM, route_json


def test_translator_sends_original_prompt_and_returns_text():
    llm = FakeLLM(translator="امروز هوا خوب است.")
    out = translator.run(SkillContext(llm, "Translate to Persian: The weather is nice today.", None, "en"))
    assert out == "امروز هوا خوب است."
    assert "The weather is nice today." in llm.user_for("translator")


def test_persian_to_english_request():
    prompt = "این جمله را به انگلیسی ترجمه کن: امروز هوا خیلی خوب است."
    llm = FakeLLM(translator="The weather is very nice today.")
    assert translator.run(SkillContext(llm, prompt, None, "fa")) == "The weather is very nice today."
    assert prompt in llm.user_for("translator")


def test_previous_step_output_becomes_the_source_text():
    llm = FakeLLM(translator="x")
    translator.run(SkillContext(llm, "Summarize and translate", "A short summary.", "en"))
    assert "<previous_step_output>\nA short summary." in llm.user_for("translator")


def test_prompt_forbids_summarizing_and_commentary():
    prompt = load_prompt("translator").lower()
    for phrase in ("never summarize", "only the translation", "zwnj", "source language"):
        assert phrase in prompt


def test_graph_flow_for_translator(make_graph):
    graph, llm = make_graph(router=route_json(["translator"], lang="fa"), translator="Hello")
    state = graph.invoke({"original_prompt": "این جمله را به انگلیسی ترجمه کن: سلام"})
    assert state["final_response"] == "Hello" and llm.roles() == ["router", "translator"]
