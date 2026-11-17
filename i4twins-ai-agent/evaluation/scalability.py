"""Scalability simulation: does routing context stay small as the registry grows?

  python -m evaluation.scalability

Uses synthetic skills (evaluation/synthetic_registry.py) and a deterministic stub instead of an
LLM, so no API key is needed. Everything reported is counted from real objects, never estimated,
except `approx_tokens`, which is simply characters / 4 and is labelled as an approximation.
The "naive" column is the size of the router prompt IF every skill's metadata AND full prompt were
injected (what the architecture avoids); it is computed from the actual strings.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from app.graph import build_graph
from app.main import run_request
from app.routing.discovery import discover
from app.routing.router import build_system_prompt, render_candidate, route_prompt
from app.utils.prompts import load_prompt
from evaluation.synthetic_registry import (FALLBACK_ID, NOUNS, VERBS, StubRouterLLM,
                                           build_synthetic_registry)

RESULTS = Path(__file__).resolve().parent / "results"
SIZES = (10, 50, 100, 200)
QUERIES = 20


def simulate(n: int, queries: int = QUERIES) -> dict:
    registry, store = build_synthetic_registry(n)
    llm = StubRouterLLM()
    graph = build_graph(llm, registry)
    template = load_prompt("router")
    skills = [s for s in registry.ids() if s != FALLBACK_ID]
    metas = registry.metadata()
    naive_chars = (len(build_system_prompt(template, metas))
                   + sum(len(store.load(m.id)) for m in metas))
    store.reset_access_log()

    rows = []
    for q in range(queries):
        target = skills[(q * 7) % len(skills)]
        noun, verb = target.split("_")
        prompt = f"Please {verb} my {noun} data now"

        store.reset_access_log()
        discovery = discover(registry, prompt, llm)                       # stage 1
        routed = route_prompt(llm, prompt, template, discovery.candidates)  # stage 2
        loaded_before_execution = len(store.accessed)

        store.reset_access_log()
        state = run_request(graph, prompt)                                # full run incl. stage 3
        selected = state.selected_skills
        rows.append({
            "candidates": len(discovery.candidates),
            "selected": len(selected),
            "loaded_before_execution": loaded_before_execution,
            "loaded_after_execution": len(store.accessed),
            "unselected_prompt_accessed": bool(store.accessed - set(selected)),
            "routing_context_chars": routed.context_chars,
            "target_in_shortlist": target in discovery.candidate_ids,
            "target_selected": selected == [target],
            "strategy": discovery.strategy,
        })

    def avg(key: str) -> float:
        return sum(r[key] for r in rows) / len(rows)

    return {
        "registered_skills": len(registry),
        "queries": queries,
        "avg_candidates": avg("candidates"),
        "avg_selected": avg("selected"),
        "max_prompts_loaded_before_execution": max(r["loaded_before_execution"] for r in rows),
        "avg_prompts_loaded_after_execution": avg("loaded_after_execution"),
        "any_unselected_prompt_accessed": any(r["unselected_prompt_accessed"] for r in rows),
        "avg_routing_context_chars": avg("routing_context_chars"),
        "naive_all_prompts_chars": naive_chars,
        "target_in_shortlist_rate": avg("target_in_shortlist"),
        "target_selected_rate": avg("target_selected"),
        "strategies": sorted({r["strategy"] for r in rows}),
    }


def render_markdown(results: list[dict]) -> str:
    lines = [
        "# Scalability simulation (synthetic skills, stub router - not a real LLM)", "",
        f"- Run at (UTC): {datetime.now(timezone.utc).isoformat(timespec='seconds')}",
        f"- {QUERIES} queries per registry size; vocabulary: {len(NOUNS)} nouns x {len(VERBS)} verbs.",
        "- `approx tokens` = characters / 4 (an approximation, not a tokenizer count).",
        "- `naive` = router prompt if EVERY skill's metadata and full prompt were injected (computed from the real strings).",
        "- Shortlist/selection rates are measured on synthetic data written by the same author: a sanity check, not a benchmark.", "",
        "| Registered (incl. 1 fallback) | Avg candidates | Avg selected | Full prompts loaded before execution (max) | Avg loaded after execution | Unselected prompt accessed | Avg routing context (chars / ~tokens) | Naive context (chars / ~tokens) | Reduction | Target in shortlist | Strategy |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in results:
        ctx, naive = r["avg_routing_context_chars"], r["naive_all_prompts_chars"]
        lines.append(
            f"| {r['registered_skills']} | {r['avg_candidates']:.1f} | {r['avg_selected']:.1f} | "
            f"{r['max_prompts_loaded_before_execution']} | {r['avg_prompts_loaded_after_execution']:.1f} | "
            f"{'YES' if r['any_unselected_prompt_accessed'] else 'no'} | {ctx:.0f} / ~{ctx / 4:.0f} | "
            f"{naive} / ~{naive // 4} | {naive / ctx:.1f}x | {r['target_in_shortlist_rate'] * 100:.0f}% | "
            f"{', '.join(r['strategies'])} |")
    return "\n".join(lines) + "\n"


def main() -> int:
    results = [simulate(n) for n in SIZES]
    RESULTS.mkdir(exist_ok=True)
    (RESULTS / "scalability.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    markdown = render_markdown(results)
    (RESULTS / "scalability.md").write_text(markdown, encoding="utf-8")
    print(markdown)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
