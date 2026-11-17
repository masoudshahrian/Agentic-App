import pytest

from app.utils.language import detect_language, normalize_text, to_ascii_digits, to_persian_digits
from tests.conftest import route_json


def test_digit_conversion():
    assert to_ascii_digits("۰۱۲۳۴۵۶۷۸۹ ٠١٢٣٤٥٦٧٨٩ 0123456789") == "0123456789 0123456789 0123456789"
    assert to_persian_digits("1200") == "۱۲۰۰"


def test_normalize_letters_punctuation_and_whitespace():
    assert normalize_text("كتاب  ي   من؟") == "کتاب ی من?"           # Arabic ك/ي -> Persian ک/ی
    assert normalize_text("۲۵ × ۴۸،") == "25 * 48,"
    assert normalize_text("ســلام") == "سلام"                         # tatweel removed
    assert normalize_text("می‌‌شود") == "می‌شود"       # duplicate ZWNJ collapsed
    assert normalize_text("کتاب‌  ها") == "کتاب ها"              # ZWNJ next to a space dropped


def test_normalize_does_not_touch_superscripts_or_latin():
    assert normalize_text("5² + Hello") == "5² + Hello"


def test_original_string_is_not_modified():
    original = "حاصل ۲۵ ضربدر ۴۸"
    normalize_text(original)
    assert original == "حاصل ۲۵ ضربدر ۴۸"


@pytest.mark.parametrize("text, lang", [
    ("سلام، حالت چطور است؟", "fa"),
    ("Hello, how are you?", "en"),
    ("۲۵*۴۸", "unknown"),                    # only digits/symbols: no guess
    ("245 * 36", "unknown"),
    ("حاصل 25 * 48 چیست؟", "fa"),           # Persian words + ASCII math
    ("Translate: سلام", "en"),              # Latin letters outnumber Persian
    ("مرحبا بك", "ar"),                      # Arabic-only letters
])
def test_detect_language(text, lang):
    assert detect_language(text) == lang


# ------------------------------------------------------------------ each skill with Persian input
def test_persian_calculator_end_to_end(make_graph):
    graph, llm = make_graph(router=route_json(["calculator"], lang="fa"),
                            calculator='{"expression": "۲۵*۴۸"}')
    state = graph.invoke({"original_prompt": "حاصل ۲۵ ضربدر ۴۸ چیست؟"})
    assert state["final_response"] == "۲۵*۴۸ = ۱۲۰۰"
    assert state["detected_language"] == "fa"


def test_persian_summarizer_end_to_end(make_graph):
    prompt = "این متن را خلاصه کن: شهرداری امروز بودجه جدید را تصویب کرد."
    graph, llm = make_graph(router=route_json(["summarizer"], lang="fa"), summarizer="بودجه تصویب شد.")
    state = graph.invoke({"original_prompt": prompt})
    assert state["final_response"] == "بودجه تصویب شد."
    assert prompt in llm.user_for("summarizer")            # original, not normalised
    assert state["original_prompt"] == prompt


def test_persian_translator_end_to_end(make_graph):
    graph, llm = make_graph(router=route_json(["translator"], lang="fa"), translator="Hello, how are you?")
    state = graph.invoke({"original_prompt": "این جمله را به انگلیسی ترجمه کن: سلام، حال شما چطور است؟"})
    assert state["final_response"] == "Hello, how are you?"


def test_persian_chat_end_to_end(make_graph):
    graph, llm = make_graph(router=route_json(["general_chat"], lang="fa"),
                            general_chat="سلام! خوبم، ممنون. شما چطورید؟")
    state = graph.invoke({"original_prompt": "سلام، حالت چطور است؟"})
    assert state["final_response"] == "سلام! خوبم، ممنون. شما چطورید؟"


def test_persian_clarification_is_returned_in_persian(make_graph):
    graph, llm = make_graph(router=route_json(["translator"], lang="fa", confidence=0.6,
                                              clarification="چه متنی را ترجمه کنم؟"))
    state = graph.invoke({"original_prompt": "ترجمه کن"})
    assert state["final_response"] == "چه متنی را ترجمه کنم؟"
    assert llm.roles() == ["router"]


def test_persian_labels_for_independent_skills(make_graph):
    graph, _ = make_graph(router=route_json(["translator", "calculator"], lang="fa"),
                          translator="Good morning", calculator='{"expression": "25*48"}')
    out = graph.invoke({"original_prompt": "صبح بخیر را به انگلیسی ترجمه کن و ۲۵ ضرب در ۴۸ را حساب کن"})
    assert "ترجمه:" in out["final_response"] and "محاسبه:" in out["final_response"]
