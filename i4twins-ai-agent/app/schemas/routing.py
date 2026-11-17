"""Pydantic models validating every structured LLM output.

Skill ids are plain strings checked against the registry at runtime (`check_against`),
not an enum, so adding a skill never requires editing this file.
"""
from __future__ import annotations

import re
from collections.abc import Mapping

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.skills.base import SkillMetadata

MAX_SKILLS_PER_REQUEST = 2
_LANG_CODE = re.compile(r"^[a-z]{2,3}$")


class RoutingDecision(BaseModel):
    """Validated output of the router (stage 2)."""

    model_config = ConfigDict(extra="ignore")

    selected_skills: list[str] = Field(default_factory=list, max_length=MAX_SKILLS_PER_REQUEST)
    depends_on_previous: bool = False
    detected_language: str
    confidence: float = Field(ge=0.0, le=1.0)
    clarification_required: bool = False
    clarification_question: str | None = None
    unsupported_request: bool = False
    unsupported_reason: str | None = None
    reasoning_summary: str = Field(default="", max_length=300)

    @field_validator("selected_skills", mode="before")
    @classmethod
    def _normalise_ids(cls, value: object) -> object:
        if isinstance(value, list):
            return [v.strip().lower() if isinstance(v, str) else v for v in value]
        return value

    @field_validator("detected_language")
    @classmethod
    def _language_code(cls, value: str) -> str:
        value = value.strip().lower()
        if not _LANG_CODE.match(value):
            raise ValueError("detected_language must be an ISO 639 code such as 'fa' or 'en'")
        return value

    @field_validator("clarification_question", "unsupported_reason", mode="before")
    @classmethod
    def _blank_is_none(cls, value: object) -> object:
        return None if isinstance(value, str) and not value.strip() else value

    @model_validator(mode="after")
    def _check_consistency(self) -> "RoutingDecision":
        if len(set(self.selected_skills)) != len(self.selected_skills):
            raise ValueError("selected_skills must not contain duplicates")
        if self.unsupported_request:
            if self.selected_skills or self.clarification_required:
                raise ValueError("an unsupported request selects no skill and needs no clarification")
            if not self.unsupported_reason:
                raise ValueError("unsupported_reason is required when unsupported_request is true")
        else:
            if not self.selected_skills and not self.clarification_required:
                raise ValueError("select at least one skill, or set unsupported_request / clarification_required")
            if self.unsupported_reason is not None:
                raise ValueError("unsupported_reason must be null unless unsupported_request is true")
        if self.depends_on_previous and len(self.selected_skills) < 2:
            raise ValueError("depends_on_previous requires two selected skills")
        if self.clarification_required and not self.clarification_question:
            raise ValueError("clarification_question is required when clarification_required is true")
        if not self.clarification_required and self.clarification_question is not None:
            raise ValueError("clarification_question must be null when clarification_required is false")
        return self

    def check_against(self, candidates: Mapping[str, SkillMetadata]) -> None:
        """Reject ids that are not among the shortlisted skills and illegal combinations."""
        unknown = [s for s in self.selected_skills if s not in candidates]
        if unknown:
            raise ValueError(f"unknown or non-shortlisted skill id(s): {', '.join(unknown)}")
        if len(self.selected_skills) > 1:
            exclusive = [s for s in self.selected_skills if candidates[s].is_fallback]
            if exclusive:
                raise ValueError(f"'{exclusive[0]}' is a fallback skill and cannot be combined with another skill")


class Shortlist(BaseModel):
    """Output of the optional LLM shortlisting step (stage 1b)."""

    model_config = ConfigDict(extra="ignore")

    candidates: list[str] = Field(default_factory=list)


class ExpressionExtraction(BaseModel):
    """Output of the calculator's extraction step (the LLM never computes the result)."""

    model_config = ConfigDict(extra="ignore")

    expression: str | None = None
    error: str | None = None

    @model_validator(mode="after")
    def _one_of(self) -> "ExpressionExtraction":
        if not (self.expression and self.expression.strip()) and not self.error:
            raise ValueError("either expression or error must be provided")
        return self
