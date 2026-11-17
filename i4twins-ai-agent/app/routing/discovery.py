"""Stage 1 - lightweight skill discovery.

Goal: shrink the registry to a handful of candidates WITHOUT loading any full skill prompt
and without sending the whole registry to the LLM.

Strategies (reported in `Discovery.strategy`):
- ``all``           the registry is small (<= FULL_LISTING_LIMIT): every compact metadata entry is a candidate.
- ``lexical``       deterministic scoring of the prompt against skill keywords/description/examples; top-K.
- ``llm_shortlist`` no lexical match and a large registry: ONE cheap LLM call sees a compact index
                    (id + short description per skill) and returns up to K ids.
- ``fallback_only`` nothing matched: only the fallback skill (general chat) is offered.
Fallback skills are always added to the candidates when the registry is large.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.llm import LLM, LLMError
from app.schemas.routing import Shortlist
from app.skills.base import SkillMetadata
from app.skills.registry import SkillRegistry
from app.utils.jsonio import StructuredOutputError, parse_model
from app.utils.language import normalize_text
from app.utils.prompts import load_prompt

MAX_CANDIDATES = 5
FULL_LISTING_LIMIT = 6
KEYWORD_WEIGHT = 3.0
OVERLAP_WEIGHT = 1.0
MAX_OVERLAP = 3
INDEX_DESCRIPTION_CHARS = 90

_TOKEN = re.compile(r"\w{4,}")


@dataclass
class Discovery:
    candidates: list[SkillMetadata]
    strategy: str
    registered: int
    notes: list[str] = field(default_factory=list)

    @property
    def candidate_ids(self) -> list[str]:
        return [m.id for m in self.candidates]


def _metadata_tokens(meta: SkillMetadata) -> set[str]:
    text = " ".join([meta.name, meta.description, *meta.operations, *meta.routing_examples]).lower()
    return set(_TOKEN.findall(normalize_text(text)))


def score(prompt: str, meta: SkillMetadata) -> float:
    """Deterministic relevance of a skill to the prompt (0 = no evidence)."""
    text = normalize_text(prompt).lower()
    keyword_hits = sum(1 for pattern in meta.keywords if re.search(pattern, text))
    overlap = len(set(_TOKEN.findall(text)) & _metadata_tokens(meta))
    return keyword_hits * KEYWORD_WEIGHT + min(overlap, MAX_OVERLAP) * OVERLAP_WEIGHT


def render_index(metas: list[SkillMetadata]) -> str:
    """Very compact one-line-per-skill index used by the LLM shortlist step."""
    return "\n".join(f"{m.id}: {m.description[:INDEX_DESCRIPTION_CHARS]}" for m in metas)


def _llm_shortlist(llm: LLM, prompt: str, registry: SkillRegistry, pool: list[SkillMetadata]) -> list[str]:
    system = load_prompt("shortlist").replace("<<MAX_CANDIDATES>>", str(MAX_CANDIDATES))
    user = f"<user_prompt>\n{prompt}\n</user_prompt>\n\nSKILL INDEX:\n{render_index(pool)}"
    shortlist = parse_model(llm.complete(system, user), Shortlist)
    unknown_dropped = [i for i in shortlist.candidates if i in registry]  # a shortlist may be lenient;
    return list(dict.fromkeys(unknown_dropped))[:MAX_CANDIDATES]          # final selection stays strict


def discover(registry: SkillRegistry, prompt: str, llm: LLM | None = None) -> Discovery:
    """Return the candidate skills for ``prompt`` (compact metadata only)."""
    metas = registry.metadata()
    total = len(metas)
    if total <= FULL_LISTING_LIMIT:
        return Discovery(metas, "all", total)

    fallbacks = [m for m in metas if m.is_fallback]
    pool = [m for m in metas if not m.is_fallback]
    ranked = sorted(((score(prompt, m), m) for m in pool), key=lambda pair: (-pair[0], pair[1].id))
    top = [m for s, m in ranked if s > 0][:MAX_CANDIDATES]
    if top:
        return Discovery([*top, *fallbacks], "lexical", total)

    notes: list[str] = []
    if llm is not None and prompt.strip():     # never spend an LLM call on an empty prompt
        try:
            ids = _llm_shortlist(llm, prompt, registry, pool)
            if ids:
                return Discovery([registry.get(i).metadata for i in ids if not registry.get(i).metadata.is_fallback]
                                 + fallbacks, "llm_shortlist", total)
            notes.append("LLM shortlist was empty")
        except (LLMError, StructuredOutputError) as exc:
            notes.append(f"LLM shortlist failed: {exc}")
    return Discovery(fallbacks, "fallback_only", total, notes)
