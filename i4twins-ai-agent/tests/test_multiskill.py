from tests.conftest import route_json

TEXT = "Long article text about the city budget and many other things."


def test_sequential_chain_passes_output_forward(make_graph):
    graph, llm = make_graph(
        router=route_json(["summarizer", "translator"], dependent=True),
        summarizer="SUMMARY-OF-TEXT",
        translator="TRANSLATED-SUMMARY",
    )
    state = graph.invoke({"original_prompt": f"Summarize this and translate the summary into Persian: {TEXT}"})
    assert llm.roles() == ["router", "summarizer", "translator"]           # strict order
    assert "SUMMARY-OF-TEXT" in llm.user_for("translator")                 # dependency honoured
    assert "<previous_step_output>" not in llm.user_for("summarizer")
    assert TEXT in llm.user_for("translator")                              # original prompt kept too
    assert state["final_response"] == "TRANSLATED-SUMMARY"                 # last step is the answer


def test_sequential_order_follows_the_router(make_graph):
    graph, llm = make_graph(
        router=route_json(["translator", "summarizer"], dependent=True),
        translator="TRANSLATION", summarizer="SUMMARY-OF-TRANSLATION",
    )
    state = graph.invoke({"original_prompt": "Translate to Persian and then summarize: " + TEXT})
    assert llm.roles() == ["router", "translator", "summarizer"]
    assert "TRANSLATION" in llm.user_for("summarizer")
    assert state["final_response"] == "SUMMARY-OF-TRANSLATION"


def test_independent_skills_run_both_and_are_labelled(make_graph):
    graph, llm = make_graph(
        router=route_json(["translator", "calculator"], dependent=False),
        translator="Bonjour", calculator='{"expression": "25*48"}',
    )
    state = graph.invoke({"original_prompt": "Translate 'good morning' into French and calculate 25 * 48."})
    assert llm.roles()[0] == "router" and set(llm.roles()) == {"router", "translator", "calculator"}
    assert "<previous_step_output>" not in llm.user_for("translator")      # no dependency
    assert "<previous_step_output>" not in llm.user_for("calculator")
    out = state["final_response"]
    assert "Translation:\nBonjour" in out and "Calculation:\n25*48 = 1200" in out
    assert out.index("Translation:") < out.index("Calculation:")           # router order kept


def test_both_skills_receive_the_original_prompt(make_graph):
    prompt = "Translate 'hi' into French and calculate 2+2"
    graph, llm = make_graph(router=route_json(["translator", "calculator"]),
                            translator="Salut", calculator='{"expression": "2+2"}')
    graph.invoke({"original_prompt": prompt})
    assert prompt in llm.user_for("translator") and prompt in llm.user_for("calculator")


def test_chain_stops_when_first_skill_fails(make_graph):
    from tests.conftest import llm_error
    graph, llm = make_graph(router=route_json(["summarizer", "translator"], dependent=True),
                            summarizer=llm_error(), translator="never called")
    state = graph.invoke({"original_prompt": "Summarize and translate: " + TEXT})
    assert llm.roles() == ["router", "summarizer"]
    assert "Sorry" in state["final_response"] and "summarizer" in state["final_response"]


def test_parallel_partial_failure_returns_the_successful_part(make_graph):
    graph, _ = make_graph(router=route_json(["translator", "calculator"]),
                          translator="Bonjour", calculator='{"expression": "1/0"}')
    out = graph.invoke({"original_prompt": "Translate hi to French and compute 1/0"})
    assert "Bonjour" in out["final_response"] and "division by zero" in out["final_response"]
    assert out["errors"]
