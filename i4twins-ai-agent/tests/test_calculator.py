import pytest

from app.skills import calculator
from app.skills.base import SkillContext, SkillError
from app.tools.safe_calculator import MAX_EXPRESSION_LENGTH, CalculatorError, calculate
from tests.conftest import FakeLLM


@pytest.mark.parametrize("expr, expected", [
    ("245 * 36", "8820"),
    ("25*48", "1200"),
    ("(3 + 4) * 2", "14"),
    ("2 ** 10", "1024"),
    ("2 ^ 10", "1024"),
    ("-5 + 3", "-2"),
    ("10 / 4", "2.5"),
    ("10 // 4", "2"),
    ("17 % 5", "2"),
    ("0.1 + 0.2", "0.3"),
    ("sqrt(144)", "12"),
    ("cbrt(27)", "3"),
    ("abs(-7.5)", "7.5"),
    ("round(3.14159, 2)", "3.14"),
    ("max(3, 9, 4)", "9"),
    ("factorial(5)", "120"),
    ("log10(1000)", "3"),
    ("pi * 2", "6.28318530718"),
    ("15% * 800", "120"),
    ("15/100*800", "120"),
    ("1,000 + 1", "1001"),
])
def test_valid_expressions(expr, expected):
    assert calculate(expr) == expected


@pytest.mark.parametrize("expr, expected", [
    ("۲۵ × ۴۸", "1200"),            # Persian digits and ×
    ("٢٥ * ٤٨", "1200"),            # Arabic-Indic digits
    ("۱۲٫۵ + ۱", "13.5"),           # Persian decimal separator
    ("۱٬۰۰۰ + ۱", "1001"),          # Persian thousands separator
    ("۱۰ ÷ ۴", "2.5"),
])
def test_persian_and_arabic_input(expr, expected):
    assert calculate(expr) == expected


@pytest.mark.parametrize("expr, message", [
    ("1/0", "division by zero"),
    ("5 % 0", "division by zero"),
    ("sqrt(-1)", "mathematical error"),
    ("log(0)", "mathematical error"),
    ("", "empty"),
    ("2 +", "could not be parsed"),
    ("hello", "unknown name"),
    ("__import__('os').system('echo hi')", "not supported"),
    ("open('x')", "not supported"),
    ("().__class__", "unsupported"),
    ("[1,2][0]", "unsupported"),
    ("lambda: 1", "unsupported"),
    ("'a' * 3", "only numbers"),
    ("True + 1", "only numbers"),
    ("x = 5", "could not be parsed"),
    ("9 ** 9 ** 9", "too large"),
    ("10 ** 1000", "too large"),
    ("factorial(10000)", "factorial"),
    ("(-8) ** 0.5", "not a real number"),
    ("1e999 * 1e999", "not a finite number"),
    ("2.0 ** 5000", "too large"),
    ("max()", "invalid function call"),
    ("sqrt(x=4)", "invalid function call"),
])
def test_invalid_or_unsafe_expressions(expr, message):
    with pytest.raises(CalculatorError, match=message):
        calculate(expr)


def test_expression_length_limit():
    with pytest.raises(CalculatorError, match="longer than"):
        calculate("1+" * MAX_EXPRESSION_LENGTH + "1")


def test_deeply_nested_parentheses_do_not_crash():
    with pytest.raises(CalculatorError):
        calculate("(" * 150 + "1" + ")" * 150)


# ------------------------------------------------------------------ the tool, not the LLM, computes
def test_result_comes_from_the_tool_not_the_llm():
    # The fake LLM "lies" with a wrong result field; only the expression is used.
    llm = FakeLLM(calculator='{"expression": "245*36", "result": 1, "error": null}')
    out = calculator.run(SkillContext(llm, "What is 245 * 36?", None, "en"))
    assert out == "245*36 = 8820" and "= 1" not in out
    assert llm.roles() == ["calculator"]           # a single LLM call: extraction only


def test_persian_request_gives_persian_digits():
    llm = FakeLLM(calculator='{"expression": "25*48", "error": null}')
    assert calculator.run(SkillContext(llm, "حاصل ۲۵ ضربدر ۴۸ چیست؟", None, "fa")) == "۲۵*۴۸ = ۱۲۰۰"


def test_percent_and_root_requests():
    llm = FakeLLM(calculator=['{"expression": "15/100*800"}', '{"expression": "sqrt(144)"}'])
    assert calculator.run(SkillContext(llm, "15 percent of 800", None, "en")).endswith("= 120")
    assert calculator.run(SkillContext(llm, "ریشه دوم ۱۴۴", None, "en")).endswith("= 12")


def test_division_by_zero_is_reported():
    llm = FakeLLM(calculator='{"expression": "5/0"}')
    with pytest.raises(SkillError, match="division by zero"):
        calculator.run(SkillContext(llm, "5 divided by 0", None, "en"))


def test_unsafe_expression_from_llm_is_rejected():
    llm = FakeLLM(calculator='{"expression": "__import__(\'os\').getcwd()"}')
    with pytest.raises(SkillError):
        calculator.run(SkillContext(llm, "do something", None, "en"))


def test_no_math_in_request():
    llm = FakeLLM(calculator='{"expression": null, "error": "no math found"}')
    with pytest.raises(SkillError, match="no math found"):
        calculator.run(SkillContext(llm, "tell me a joke", None, "en"))


def test_extraction_retry_on_malformed_json():
    llm = FakeLLM(calculator=["sure! 4", '{"expression": "2+2"}'])
    assert calculator.run(SkillContext(llm, "2 plus 2", None, "en")) == "2+2 = 4"
    assert len(llm.calls) == 2


def test_extraction_fails_after_two_bad_replies():
    llm = FakeLLM(calculator="nope")
    with pytest.raises(SkillError, match="could not understand"):
        calculator.run(SkillContext(llm, "2 plus 2", None, "en"))
