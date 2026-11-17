from __future__ import annotations

from app.skills.base import Skill, SkillContext, SkillMetadata
from app.skills.common import build_user_message
from app.utils.prompts import load_prompt

METADATA = SkillMetadata(
    id="general_chat",
    name="General Chat",
    description="Greetings, small talk, general-knowledge questions and explanations. Cannot take actions or use live data.",
    input_types=["text"],
    operations=["converse", "explain"],
    routing_examples=["Hello, how are you?", "سلام، حالت چطور است؟", "What is a prime number?"],
    keywords=[],
    routing_hint=(
        "Use for conversation and questions that can be answered from general knowledge, including "
        "explaining math concepts. Not for tasks that need actions, live data, files or accounts."
    ),
    is_fallback=True,
    result_labels={"en": "Answer", "fa": "پاسخ"},
)


def run(ctx: SkillContext) -> str:
    """Answer a greeting or general question."""
    user = build_user_message(ctx.prompt, ctx.previous_output, ctx.language)
    return ctx.llm.complete(load_prompt("general_chat"), user).strip()


SKILL = Skill(METADATA, run)
