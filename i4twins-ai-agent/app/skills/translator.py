from __future__ import annotations

from app.skills.base import Skill, SkillContext, SkillMetadata
from app.skills.common import build_user_message
from app.utils.prompts import load_prompt

METADATA = SkillMetadata(
    id="translator",
    name="Translator",
    description="Translates a given text between languages (Persian, English and others) keeping meaning and tone.",
    input_types=["text"],
    operations=["translate", "detect_language"],
    routing_examples=[
        "Translate to Persian: Hello, how are you?",
        "این جمله را به انگلیسی ترجمه کن: <جمله>",
        "How do you say 'thank you' in French?",
    ],
    keywords=[
        r"translat", r"ترجمه",
        r"(?:in|into|to) (?:english|persian|farsi|french|german|arabic)",
        r"به (?:زبان )?(?:انگلیسی|فارسی|عربی|فرانسه|آلمانی)",
    ],
    routing_hint=(
        "If no target language is named it can be inferred (Persian text -> English, other -> Persian): "
        "do not ask. Ask only when the text to translate is missing."
    ),
    accepts_previous_output=True,
    requires_content=True,
    missing_input_question={
        "en": "Which text should I translate, and into which language?",
        "fa": "چه متنی را و به چه زبانی ترجمه کنم؟",
    },
    result_labels={"en": "Translation", "fa": "ترجمه"},
)


def run(ctx: SkillContext) -> str:
    """Translate the text in the prompt (or in the previous step's output)."""
    user = build_user_message(ctx.prompt, ctx.previous_output, ctx.language)
    return ctx.llm.complete(load_prompt("translator"), user).strip()


SKILL = Skill(METADATA, run)
