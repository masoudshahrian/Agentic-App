"""Robust JSON extraction + Pydantic validation for LLM replies."""
from __future__ import annotations

import json
import re
from typing import TypeVar

from pydantic import BaseModel, ValidationError

T = TypeVar("T", bound=BaseModel)

_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE)


class StructuredOutputError(ValueError):
    """The reply was not valid JSON or did not satisfy the schema."""


def parse_model(raw: str, model: type[T]) -> T:
    """Extract the first JSON object in ``raw`` and validate it as ``model``."""
    text = _FENCE.sub("", raw.strip()).strip()
    start = text.find("{")
    if start < 0:
        raise StructuredOutputError("no JSON object found in the reply")
    try:
        data, _ = json.JSONDecoder().raw_decode(text[start:])
    except json.JSONDecodeError as exc:
        raise StructuredOutputError(f"invalid JSON: {exc.msg}") from None
    if not isinstance(data, dict):
        raise StructuredOutputError("the JSON value must be an object")
    try:
        return model.model_validate(data)
    except ValidationError as exc:
        problems = "; ".join(f"{'.'.join(map(str, e['loc'])) or 'root'}: {e['msg']}" for e in exc.errors())
        raise StructuredOutputError(problems[:500]) from None
