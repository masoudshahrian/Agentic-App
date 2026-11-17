# CLAUDE.md - instructions for the AI coding assistant

This repository was built with Claude Code. This file records the standing instructions the assistant worked
under. Specs: [PROJECT_SPEC.md](PROJECT_SPEC.md) (original brief),
[INTERVIEWER_REQUIREMENTS.md](INTERVIEWER_REQUIREMENTS.md) (clarifications), [ARCHITECTURE.md](ARCHITECTURE.md).

## Commands

```bash
python -m pytest                                  # offline tests (fake LLM), must pass before merging
python -m evaluation.evaluate --offline           # keyword-router baseline, no key
python -m evaluation.evaluate                     # live routing evaluation (needs OPENROUTER_API_KEY)
python -m evaluation.scalability                  # context-management simulation (synthetic skills)
python main.py "..."                              # CLI
```

## Rules

1. Exactly four user-facing skills (summarizer, translator, calculator, general_chat); at most two per request.
   Synthetic skills exist only in `evaluation/synthetic_registry.py`.
2. Never put skill-specific logic in the router, edges, graph builder, state or schemas. Skill knowledge (keywords,
   hints, labels, prompts) lives in the skill's own module in `app/skills/`.
3. The router receives only compact `SkillMetadata` of the shortlisted candidates, never a full skill prompt.
   Skill prompts are loaded lazily by the selected skill's handler via `load_prompt` / `PromptStore`.
4. The LLM never produces calculator results; `app/tools/safe_calculator.py` does. No `eval`/`exec`.
5. Do not invent measurements. Numbers in README/docs must come from a real run of the evaluation commands;
   say "not measured" when a live key was not available.
6. Never commit secrets; configuration comes from `.env` (`.env.example` has placeholders).
7. Do not create a remote repository or push without the author's explicit authorisation.
8. Keep code small and typed; prompts in `app/prompts/` (one file per prompt, no duplication); update the docs and the
   compliance matrix when behaviour changes.
9. No database, persistence, cross-request memory, web API or auth. (The local Streamlit UI in `ui.py` calls the graph in-process, bound to localhost; it is not a web API.)

## Layout

`app/skills/` skill plugins + registry - `app/routing/` discovery (stage 1), router (stage 2), keyword fallback -
`app/graph/` state, nodes, edges, builder - `app/schemas/` Pydantic models - `app/tools/` calculator -
`app/utils/` language, JSON, prompts, bidi - `app/models.py` + `app/compare.py` UI model list and side-by-side runner - `ui.py` Streamlit UI - `evaluation/` dataset, metrics, simulation - `tests/`.
