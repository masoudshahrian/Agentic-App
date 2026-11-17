from app.skills.base import SkillContext
from app.skills import summarizer
from app.utils.prompts import load_prompt
from tests.conftest import FakeLLM, route_json

TEXT = "The city council met on Tuesday. It approved a new budget of 4.1 million dollars for road repairs."


def test_summarizer_uses_its_own_prompt_and_original_text():
    llm = FakeLLM(summarizer="  The council approved a $4.1M road budget.  ")
    out = summarizer.run(SkillContext(llm, f"Summarize this: {TEXT}", None, "en"))
    assert out == "The council approved a $4.1M road budget."
    assert llm.roles() == ["summarizer"]
    assert TEXT in llm.user_for("summarizer")


def test_previous_output_is_passed_as_the_text_to_summarize():
    llm = FakeLLM(summarizer="ok")
    summarizer.run(SkillContext(llm, "translate then summarize", "Previous translation text", "en"))
    assert "<previous_step_output>\nPrevious translation text" in llm.user_for("summarizer")


def test_persian_text_reaches_the_model_unchanged():
    prompt = "این متن را خلاصه کن: شهرداری امروز بودجه جدید را تصویب کرد."
    llm = FakeLLM(summarizer="شهرداری بودجه را تصویب کرد.")
    assert summarizer.run(SkillContext(llm, prompt, None, "fa")) == "شهرداری بودجه را تصویب کرد."
    assert prompt in llm.user_for("summarizer")
    assert "<user_language>fa</user_language>" in llm.user_for("summarizer")


def test_graph_flow_for_summarizer(make_graph):
    graph, llm = make_graph(router=route_json(["summarizer"]), summarizer="Short summary.")
    state = graph.invoke({"original_prompt": f"Summarize this article. {TEXT}"})
    assert state["final_response"] == "Short summary."
    assert llm.roles() == ["router", "summarizer"]


def test_prompt_contract_mentions_faithfulness_and_length():
    prompt = load_prompt("summarizer").lower()
    for phrase in ("never add facts", "length", "persian", "only the summary"):
        assert phrase in prompt
