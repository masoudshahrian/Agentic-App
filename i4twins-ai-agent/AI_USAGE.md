# AI usage disclosure

This project was designed, implemented, tested and documented with **Claude Code** (Anthropic's AI coding
assistant; model Claude Sonnet 5.5), working from the I4Twins technical-task brief, a detailed implementation
prompt, and the interviewer's later clarifications. **The code was not written manually by the author; it was
AI-generated and then reviewed/run by the author's workflow as described below.** The author remains responsible for
the submission.

## AI-assisted tasks

- Requirements analysis and conversion into specs ([PROJECT_SPEC.md](PROJECT_SPEC.md),
  [INTERVIEWER_REQUIREMENTS.md](INTERVIEWER_REQUIREMENTS.md)).
- Architecture and interfaces ([ARCHITECTURE.md](ARCHITECTURE.md)): skill registry, two-stage routing, constant graph.
- All source code under `app/` and the Streamlit UI (`ui.py`), all prompts under `app/prompts/`, the tests, the evaluation and simulation scripts.
- All documentation, including this file, the README and the compliance matrix.
- Git branches and commits (created locally; nothing was pushed).
- A model/pricing check: the assistant queried OpenRouter's public model list (no key, no personal data sent).

## Decisions made with assistant proposals and reviewed against the specs

- Skill contract (metadata/handler split) and plugin-style registration.
- Stage-1 strategy (lexical first, LLM shortlist only when nothing matches); no vector database.
- Constant four-node graph using `Send`; chaining guarded by `accepts_previous_output`.
- Unsupported-request outcome reconciling the interviewer's "return an error" with General Chat.
- Honest reporting policy: unmeasured items are labelled "not measured".

An independent architecture review pass was performed by the assistant against the specs after implementation
(see README "Architecture review"). It is an AI self-review, not a human or third-party review.

## How generated code was tested and validated

- Offline pytest suite with a scripted fake LLM (run result is stated in the README).
- Offline evaluation of the deterministic keyword router and the scalability simulation (counted from real objects).
- CLI exercised with a fake LLM for Persian, sequential and parallel requests; `--help` and missing-key paths run for real.
- A live routing evaluation (final and naive v1 router prompts) was run later with an OpenRouter key and `google/gemma-4-31b-it`; results are in README section 8.
- **Only spot-checked:** answer quality and Persian output quality (four prompts, no systematic review).

## Runtime LLM

`google/gemma-4-31b-it:free` through OpenRouter (see README for verification details).
