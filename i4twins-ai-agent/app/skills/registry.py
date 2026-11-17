"""Central skill registry: registration, validation and discovery."""
from __future__ import annotations

from collections.abc import Iterator

from app.skills.base import Skill, SkillMetadata


class RegistryError(ValueError):
    """Invalid registration or lookup of an unknown skill."""


class SkillRegistry:
    def __init__(self, skills: list[Skill] | None = None) -> None:
        self._skills: dict[str, Skill] = {}
        for skill in skills or []:
            self.register(skill)

    def register(self, skill: Skill) -> None:
        if not isinstance(skill, Skill):
            raise RegistryError(f"expected a Skill, got {type(skill).__name__}")
        if skill.id in self._skills:
            raise RegistryError(f"duplicate skill id '{skill.id}'")
        if skill.metadata.is_fallback and self.fallback() is not None:
            raise RegistryError(f"only one fallback skill is allowed (already '{self.fallback().id}')")
        self._skills[skill.id] = skill

    def get(self, skill_id: str) -> Skill:
        try:
            return self._skills[skill_id]
        except KeyError:
            raise RegistryError(f"unknown skill id '{skill_id}'") from None

    def __contains__(self, skill_id: object) -> bool:
        return skill_id in self._skills

    def __len__(self) -> int:
        return len(self._skills)

    def __iter__(self) -> Iterator[Skill]:
        return iter(self._skills.values())

    def ids(self) -> list[str]:
        return list(self._skills)

    def metadata(self) -> list[SkillMetadata]:
        """Compact metadata of every skill (never the execution prompts)."""
        return [skill.metadata for skill in self._skills.values()]

    def fallback(self) -> Skill | None:
        return next((s for s in self._skills.values() if s.metadata.is_fallback), None)
