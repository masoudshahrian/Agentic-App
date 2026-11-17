"""Helpers shared by LLM-backed skills."""
from __future__ import annotations


def build_user_message(prompt: str, previous_output: str | None, language: str) -> str:
    """Wrap the ORIGINAL prompt (and the previous step's output) in labelled data tags."""
    parts = [f"<user_language>{language}</user_language>", f"<original_request>\n{prompt}\n</original_request>"]
    if previous_output:
        parts.append(f"<previous_step_output>\n{previous_output}\n</previous_step_output>")
    return "\n".join(parts)
