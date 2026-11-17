# Implementation plan (specification-driven workflow)

Workflow followed: analyse requirements -> write explicit specs ([PROJECT_SPEC.md](PROJECT_SPEC.md),
[INTERVIEWER_REQUIREMENTS.md](INTERVIEWER_REQUIREMENTS.md)) -> design ([ARCHITECTURE.md](ARCHITECTURE.md)) ->
define contracts (`SkillMetadata`, `Skill`, `RoutingDecision`, `AgentState`, `SkillTask`) -> implement
incrementally -> run tests -> review against the specs -> update docs -> prepare submission.

## Phase history (what was actually done)

| Phase | Result | Branch / commits |
|---|---|---|
| 1. Baseline | Config, LLM wrapper, Pydantic schemas, Persian utils, safe calculator, four skills, first LangGraph graph (one node per skill), CLI, 15-prompt evaluation, README | `main` (initial commits) |
| 2. Interviewer clarifications | Skill contract + metadata validation + central registry + plugin discovery | `feature/skill-registry` |
| 3. Two-stage routing | Stage-1 discovery (all / lexical / LLM shortlist / fallback-only), generic router prompt rendered from candidate metadata, validation against the shortlist, unsupported-request outcome | `feature/skill-registry` |
| 4. Graph redesign | Constant-size graph `discover -> router -> execute_skill -> aggregator`; parallel via `Send`, sequential via conditional edge | `feature/skill-registry` |
| 5. Evidence | Scalability simulation (synthetic registries), registry/discovery/lazy-loading/unsupported tests, offline evaluation refresh | `feature/scalability-tests` |
| 6. Documentation | Specs, architecture, query categories, README section + compliance matrix, AI usage, CLAUDE.md | `docs/project-documentation` |

## Design decisions (and rejected alternatives)

| Decision | Why | Rejected |
|---|---|---|
| Metadata/handler split; prompts loaded lazily in the handler | The router can never see full prompts; unselected skills cost nothing | One big registry of prompts |
| Plugin discovery of `SKILL` in `app/skills/*` | Adding a skill = adding a file | A central dict edited for each skill |
| Constant 4-node graph with `Send` | Graph complexity independent of N | One node and edge set per skill |
| Stage 1 = lexical scoring, LLM shortlist only when nothing matches | No extra LLM call in the common path; compact index when needed | Embeddings/vector DB (out of scope for a prototype), sending all metadata always |
| Skill ids are strings validated at runtime | No enum to edit per skill | `Skill` enum |
| `accepts_previous_output` metadata guards chaining | Dependency decision grounded in metadata | Trusting the LLM's `depends_on_previous` blindly |
| `unsupported_request` outcome | Satisfies "return an error when no skill fits" without breaking General Chat | Forcing every prompt into chat or into a skill |

## Testing strategy

- Offline unit tests with a scripted fake LLM keyed by prompt role (`tests/conftest.py`): schemas, router retry/fallback,
  calculator safety, skills, Persian per skill, sequential/parallel flows, registry and discovery, lazy loading,
  unsupported/ambiguous handling, configuration, evaluation metrics.
- Scalability simulation (`evaluation/scalability.py`) with synthetic registries and a stub router.
- Offline evaluation of the keyword router (`--offline`); live LLM evaluation is implemented but not yet run.
- These tests validate code and architecture, **not** LLM answer quality.

## Remaining (needs the author)

Live LLM runs (OpenRouter key), manual quality review, publishing the repository. See README "Remaining actions".
