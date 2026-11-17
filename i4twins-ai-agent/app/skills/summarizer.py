from __future__ import annotations

from app.skills.base import Skill, SkillContext, SkillMetadata
from app.skills.common import build_user_message
from app.utils.prompts import load_prompt

METADATA = SkillMetadata(
    id="summarizer",
    name="Summarizer",
    description="Condenses a given text (article, email, report) into a shorter faithful summary.",
    input_types=["text"],
    operations=["summarize", "key_points"],
    routing_examples=[
        "Summarize this article: <text>",
        "این متن را خلاصه کن: <متن>",
        "Give me the key points of the text below",
    ],
    keywords=[r"summar", r"tl;?dr", r"key points", r"خلاصه", r"چکیده"],
    routing_hint="Numbers or arithmetic inside the text to summarize do not make it a calculation.",
    accepts_previous_output=True,
    requires_content=True,
    missing_input_question={"en": "Which text would you like me to summarize?", "fa": "کدام متن را خلاصه کنم؟"},
    result_labels={"en": "Summary", "fa": "خلاصه"},
)


def run(ctx: SkillContext) -> str:
    """Summarize the text in the prompt (or in the previous step's output)."""
    user = build_user_message(ctx.prompt, ctx.previous_output, ctx.language)
    return ctx.llm.complete(load_prompt("summarizer"), user).strip()


SKILL = Skill(METADATA, run)
