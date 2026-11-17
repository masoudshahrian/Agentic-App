"""Routing evaluation on the fixed 15-prompt dataset.

  python -m evaluation.evaluate                 # live LLM router (needs OPENROUTER_API_KEY)
  python -m evaluation.evaluate --offline       # deterministic keyword router (no API key)
  python -m evaluation.evaluate --router-prompt evaluation/router_v1_naive.txt   # A/B a prompt

Only the router is evaluated. Results are written to evaluation/results/ and are never
hand-edited: the numbers in the README must be copied from these files.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from app.config import ConfigError
from app.routing.discovery import discover
from app.routing.heuristic import heuristic_route
from app.routing.router import route_prompt
from app.skills import build_default_registry
from app.llm import LLMError
from app.main import create_llm
from app.utils.prompts import load_prompt
from evaluation.metrics import Record, compute_metrics

ROOT = Path(__file__).resolve().parent
DATASET = ROOT / "dataset.json"
RESULTS = ROOT / "results"


def _pct(value: float | None) -> str:
    return "n/a" if value is None else f"{value * 100:.1f}%"


def _route_with_patience(llm, prompt, router_prompt, candidates, wait: float, attempts: int = 12):
    """Retry provider failures (rate limits); never score an API failure as a routing error."""
    for attempt in range(attempts):
        result = route_prompt(llm, prompt, router_prompt, candidates)
        if result.decision is not None:
            return result
        print(f"  provider failure ({result.errors[-1]}); waiting {wait:.0f}s ({attempt + 1}/{attempts})", file=sys.stderr)
        time.sleep(wait)
    raise LLMError("provider kept failing; the evaluation was aborted and nothing was recorded")


def evaluate(mode: str, router_prompt: str, delay: float, wait: float = 30.0) -> dict:
    cases = json.loads(DATASET.read_text(encoding="utf-8"))
    llm = None if mode == "offline" else create_llm()
    registry = build_default_registry()
    records, details = [], []
    for case in cases:
        if llm is None:
            decision, source, errors = heuristic_route(case["prompt"], registry.metadata()), "heuristic", []
        else:
            candidates = discover(registry, case["prompt"], llm).candidates
            result = _route_with_patience(llm, case["prompt"], router_prompt, candidates, wait)
            decision, source, errors = result.decision, result.source, result.errors
            time.sleep(delay)  # free-tier rate limits
        predicted = tuple(decision.selected_skills) if decision else ()
        clarification = bool(decision and decision.clarification_required)
        unsupported = bool(decision and decision.unsupported_request)
        records.append(Record(tuple(case["expected_skills"]), predicted, case["clarification_required"],
                              clarification, case["expected_language"],
                              case.get("expected_unsupported", False), unsupported))
        details.append({
            "id": case["id"], "prompt": case["prompt"][:80], "expected": case["expected_skills"],
            "predicted": list(predicted), "expected_clarification": case["clarification_required"],
            "predicted_clarification": clarification, "expected_unsupported": case.get("expected_unsupported", False),
            "predicted_unsupported": unsupported, "source": source,
            "match": set(predicted) == set(case["expected_skills"]), "errors": errors,
        })
    return {"mode": mode, "run_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "metrics": compute_metrics(records), "details": details}


def render_markdown(report: dict, label: str) -> str:
    m = report["metrics"]
    lines = [
        f"# Routing evaluation — {label}", "",
        f"- Run at (UTC): {report['run_at']}", f"- Prompts: {m['n']}", "",
        "| Metric | Value |", "|---|---|",
        f"| Exact skill-set accuracy | {_pct(m['exact_skill_set_accuracy'])} |",
        f"| Multi-skill detection accuracy (n={m['multi_skill_n']}) | {_pct(m['multi_skill_detection_accuracy'])} |",
        f"| Clarification decision accuracy | {_pct(m['clarification_accuracy'])} |",
        f"| Unsupported-request decision accuracy | {_pct(m['unsupported_accuracy'])} |",
        f"| Persian routing accuracy (n={m['persian_n']}) | {_pct(m['persian_routing_accuracy'])} |", "",
        "| Skill | Precision | Recall | F1 | Support |", "|---|---|---|---|---|",
    ]
    for skill, s in m["per_skill"].items():
        lines.append(f"| {skill} | {_pct(s['precision'])} | {_pct(s['recall'])} | {_pct(s['f1'])} | {s['support']} |")
    lines += ["", "| # | Expected | Predicted | Clarify (exp/pred) | Unsupported (exp/pred) | OK |", "|---|---|---|---|---|---|"]
    for d in report["details"]:
        lines.append(f"| {d['id']} | {', '.join(d['expected'])} | {', '.join(d['predicted']) or '-'} | "
                     f"{d['expected_clarification']}/{d['predicted_clarification']} | "
                     f"{d['expected_unsupported']}/{d['predicted_unsupported']} | {'yes' if d['match'] else '**NO**'} |")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--offline", action="store_true", help="evaluate the deterministic keyword router, no API key")
    parser.add_argument("--router-prompt", type=Path, help="router prompt file to evaluate (default: app/prompts/router.txt)")
    parser.add_argument("--wait", type=float, default=30.0, help="seconds to wait before retrying a provider failure")
    parser.add_argument("--delay", type=float, default=3.0, help="seconds between live calls (free-tier rate limit)")
    args = parser.parse_args(argv)

    mode = "offline" if args.offline else "live"
    prompt_name = args.router_prompt.stem if args.router_prompt else "router"
    router_prompt = args.router_prompt.read_text(encoding="utf-8").strip() if args.router_prompt else load_prompt("router")
    if args.router_prompt and "ROLE: router" not in router_prompt:
        router_prompt = "ROLE: router\n" + router_prompt
    try:
        report = evaluate(mode, router_prompt, args.delay, args.wait)
    except (ConfigError, LLMError) as exc:
        print(f"Live evaluation not run: {exc}\nUse --offline for the keyword-router baseline.", file=sys.stderr)
        return 2

    label = "deterministic keyword router (no LLM)" if mode == "offline" else f"live LLM router, prompt '{prompt_name}'"
    stem = "offline_baseline" if mode == "offline" else f"live_{prompt_name}"
    RESULTS.mkdir(exist_ok=True)
    (RESULTS / f"{stem}.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    markdown = render_markdown(report, label)
    (RESULTS / f"{stem}.md").write_text(markdown, encoding="utf-8")
    print(markdown)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
