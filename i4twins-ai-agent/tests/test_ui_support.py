from app.compare import run_models
from app.graph import AgentState
from app.models import MODEL_CHOICES, choice_by_label
from app.utils.bidi import is_rtl, to_html


def test_persian_lines_are_rtl_and_english_or_numbers_are_ltr():
    assert is_rtl("سلام دنیا")
    assert is_rtl("Hello سلام")            # any Persian letter makes the line right-to-left
    assert not is_rtl("Hello world")
    assert not is_rtl("144")
    assert not is_rtl("۱۵/۱۰۰*۲۴۰+۷ = ۴۳")  # digits alone never flip the direction


def test_to_html_sets_direction_per_line_and_escapes():
    html = to_html("سلام\nHello <b>x</b>\n\n42")
    assert 'dir="rtl" style="text-align:right">سلام' in html
    assert 'dir="ltr" style="text-align:left">Hello &lt;b&gt;x&lt;/b&gt;' in html
    assert 'dir="ltr" style="text-align:left">42' in html


def test_run_models_isolates_failures_and_keeps_order():
    def run_one(model_id, prompt):
        if model_id == "bad":
            raise RuntimeError("boom")
        return AgentState(original_prompt=prompt, final_response=f"{model_id}:{prompt}", selected_skills=["calculator"])

    first, second = run_models("x", ["good", "bad"], run_one)
    assert (first.model_id, first.answer, first.skills, first.kind) == ("good", "good:x", "calculator", "answer")
    assert (second.model_id, second.kind) == ("bad", "error") and "boom" in second.answer


def test_model_choices_include_a_qwen_and_are_unique():
    ids = [c.model_id for c in MODEL_CHOICES]
    assert len(ids) == len(set(ids)) and any(i.startswith("qwen/") for i in ids)
    assert choice_by_label(MODEL_CHOICES[0].label) is MODEL_CHOICES[0]
