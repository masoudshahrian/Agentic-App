"""Skill plugins and the default registry.

Every module in this package that defines a module-level ``SKILL`` is registered
automatically, so adding a skill = adding one file here (no router or graph changes).
"""
from __future__ import annotations

import importlib
import pkgutil

from app.skills.base import Skill
from app.skills.registry import SkillRegistry

_NOT_SKILLS = {"base", "common", "registry"}


def discover_builtin_skills() -> list[Skill]:
    skills = []
    for module_info in sorted(pkgutil.iter_modules(__path__), key=lambda m: m.name):
        if module_info.name in _NOT_SKILLS:
            continue
        module = importlib.import_module(f"{__name__}.{module_info.name}")
        skill = getattr(module, "SKILL", None)
        if skill is not None:
            skills.append(skill)
    return skills


def build_default_registry() -> SkillRegistry:
    """Registry with the four skills required by the assessment."""
    return SkillRegistry(discover_builtin_skills())
