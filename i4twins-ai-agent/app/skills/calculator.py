"""Calculator skill: the LLM only extracts an expression; the tool computes the result."""
from __future__ import annotations

from app.llm import LLM
from app.schemas.routing import ExpressionExtraction
from app.skills.base import Skill, SkillContext, SkillError, SkillMetadata
from app.skills.common import build_user_message
from app.tools.safe_calculator import CalculatorError, calculate, prepare
from app.utils.jsonio import StructuredOutputError, parse_model
from app.utils.language import to_persian_digits
from app.utils.prompts import load_prompt

METADATA = SkillMetadata(
    id="calculator",
    name="Calculator",
    description="Computes arithmetic, percentages, powers, roots and other math with an exact tool.",
    input_types=["text", "math_expression"],
    operations=["arithmetic", "percentage", "power", "root"],
    routing_examples=["What is 245 * 36?", "حاصل ۲۵ ضربدر ۴۸ چیست؟", "Calculate 15 percent of 800"],
    keywords=[
        r"calculat", r"compute", r"percent", r"sqrt", r"square root",
        r"حساب کن", r"محاسبه", r"ضرب", r"تقسیم بر", r"به توان", r"ریشه", r"درصد", r"حاصل",
        r"\d\s*(?:[-+*/^%]|\*\*)\s*\d",
    ],
    routing_hint="Only for computing a number. Explaining a math concept (what is a prime number?) is not a calculation.",
    result_labels={"en": "Calculation", "fa": "محاسبه"},
)


def _extract(llm: LLM, system: str, user: str) -> ExpressionExtraction:
    try:
        return parse_model(llm.complete(system, user), ExpressionExtraction)
    except StructuredOutputError as exc:  # one corrective retry, as in the router
        retry = f"{user}\n\nYour previous reply was invalid ({exc}). Reply with ONLY the JSON object."
        try:
            return parse_model(llm.complete(system, retry), ExpressionExtraction)
        except StructuredOutputError as exc2:
            raise SkillError(f"could not understand the calculation ({exc2})") from None


def run(ctx: SkillContext) -> str:
    """Return ``"<expression> = <result>"``; the number always comes from `calculate`."""
    user = build_user_message(ctx.prompt, ctx.previous_output, ctx.language)
    extraction = _extract(ctx.llm, load_prompt("calculator"), user)
    if not extraction.expression:
        raise SkillError(extraction.error or "no calculation found in the request")
    try:
        result = calculate(extraction.expression)
    except CalculatorError as exc:
        raise SkillError(str(exc)) from None
    line = f"{prepare(extraction.expression)} = {result}"
    return to_persian_digits(line) if ctx.language == "fa" else line


SKILL = Skill(METADATA, run)
