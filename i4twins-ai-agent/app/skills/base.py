"""The skill contract: compact routing metadata + an execution handler.

Routing only ever sees `SkillMetadata`. The full instructions (prompt files, tools) live
behind the handler and are loaded lazily when the skill actually runs.
"""
from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.llm import LLM

_ID = re.compile(r"^[a-z][a-z0-9_]{1,39}$")
MAX_EXAMPLE_LENGTH = 120


class SkillError(RuntimeError):
    """A skill could not produce a result (message is shown to the user)."""


class SkillMetadata(BaseModel):
    """Everything the router may know about a skill. Kept deliberately small."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str                                                    # unique identifier, e.g. "translator"
    name: str = Field(min_length=1, max_length=40)
    description: str = Field(min_length=10, max_length=200)
    input_types: list[str] = Field(min_length=1)               # e.g. ["text"], ["math_expression"]
    operations: list[str] = Field(min_length=1)                # e.g. ["translate", "detect_language"]
    routing_examples: list[str] = Field(min_length=1, max_length=4)
    keywords: list[str] = Field(default_factory=list)          # regexes for stage-1 discovery (en + fa)
    routing_hint: str = Field(default="", max_length=240)      # boundary rule shown to the router
    is_fallback: bool = False          # handles "everything else"; never combined with another skill
    accepts_previous_output: bool = False   # can work on another skill's output (enables chaining)
    requires_content: bool = False     # needs text beyond the instruction (else ask the user)
    missing_input_question: dict[str, str] = Field(default_factory=dict)   # lang -> question
    result_labels: dict[str, str] = Field(default_factory=dict)            # lang -> section label

    @field_validator("id")
    @classmethod
    def _valid_id(cls, value: str) -> str:
        if not _ID.match(value):
            raise ValueError("id must be lowercase snake_case, 2-40 chars, starting with a letter")
        return value

    @field_validator("routing_examples")
    @classmethod
    def _short_examples(cls, values: list[str]) -> list[str]:
        if any(not v.strip() or len(v) > MAX_EXAMPLE_LENGTH for v in values):
            raise ValueError(f"routing examples must be 1-{MAX_EXAMPLE_LENGTH} characters")
        return values

    @field_validator("keywords")
    @classmethod
    def _compilable_keywords(cls, values: list[str]) -> list[str]:
        for pattern in values:
            try:
                re.compile(pattern)
            except re.error as exc:
                raise ValueError(f"invalid keyword regex {pattern!r}: {exc}") from None
        return values

    @model_validator(mode="after")
    def _consistent(self) -> "SkillMetadata":
        if self.requires_content and "en" not in self.missing_input_question:
            raise ValueError("requires_content skills need an English missing_input_question")
        if self.is_fallback and self.requires_content:
            raise ValueError("a fallback skill cannot require content")
        return self


@dataclass(frozen=True)
class SkillContext:
    """What a skill receives: the ORIGINAL prompt plus any explicitly required earlier output."""

    llm: LLM
    prompt: str
    previous_output: str | None = None
    language: str = "unknown"


Handler = Callable[[SkillContext], str]


@dataclass(frozen=True)
class Skill:
    metadata: SkillMetadata
    handler: Handler

    def __post_init__(self) -> None:
        if not isinstance(self.metadata, SkillMetadata):
            raise TypeError("Skill.metadata must be a SkillMetadata")
        if not callable(self.handler):
            raise TypeError("Skill.handler must be callable")

    @property
    def id(self) -> str:
        return self.metadata.id

    def run(self, context: SkillContext) -> str:
        return self.handler(context)
