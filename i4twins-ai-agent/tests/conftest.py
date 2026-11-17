"""Shared test helpers: a scripted fake LLM keyed by the `ROLE:` line of each prompt."""
from __future__ import annotations

import json
import re
import threading

import pytest

from app.graph import build_graph
from app.llm import LLMError

_ROLE = re.compile(r"^ROLE:\s*(\w+)", re.MULTILINE)


def route_json(skills, *, dependent=False, lang="en", confidence=0.95,
               clarification=None, unsupported=None, reason="test") -> str:
    return json.dumps({
        "selected_skills": skills, "depends_on_previous": dependent, "detected_language": lang,
        "confidence": confidence, "clarification_required": clarification is not None,
        "clarification_question": clarification, "unsupported_request": unsupported is not None,
        "unsupported_reason": unsupported, "reasoning_summary": reason,
    }, ensure_ascii=False)


class FakeLLM:
    """Replies per role. A reply may be a string, a list of strings (consumed in order,
    the last one repeats), an Exception instance (raised), or a callable(user) -> str."""

    def __init__(self, **replies):
        self.replies = replies
        self.calls: list[tuple[str, str]] = []   # (role, user message)
        self.systems: list[tuple[str, str]] = []  # (role, system prompt)
        self._lock = threading.Lock()

    def complete(self, system: str, user: str) -> str:
        role = _ROLE.search(system).group(1)
        with self._lock:
            self.calls.append((role, user))
            self.systems.append((role, system))
            reply = self.replies[role]
            if isinstance(reply, list):
                reply = reply.pop(0) if len(reply) > 1 else reply[0]
        if isinstance(reply, Exception):
            raise reply
        return reply(user) if callable(reply) else reply

    def roles(self) -> list[str]:
        return [role for role, _ in self.calls]

    def system_for(self, role: str) -> str:
        return next(system for r, system in self.systems if r == role)

    def user_for(self, role: str) -> str:
        return next(user for r, user in self.calls if r == role)


@pytest.fixture
def make_graph():
    def _make(**replies):
        llm = FakeLLM(**replies)
        return build_graph(llm), llm
    return _make


def llm_error() -> LLMError:
    return LLMError("rate limit reached (test)")
