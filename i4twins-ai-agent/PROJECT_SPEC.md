# Project specification: I4Twins "Technical Task: AI Engineer"

> Source note: this is the specification **as summarised in the instructions handed to the AI assistant**
> (original brief: "Technical Task: AI Engineer"). It is a faithful summary, not the verbatim PDF. The
> interviewer's later clarifications are in [INTERVIEWER_REQUIREMENTS.md](INTERVIEWER_REQUIREMENTS.md).
> Each requirement has an ID used by the compliance matrix in the README.

Build an early prototype of a multi-skill agent: a free-form prompt comes in, the agent detects which
skill(s) apply and answers using them.

| ID | Requirement |
|---|---|
| O-1 | Exactly 4 skills: Summarizer, Translator, Calculator (a real computational tool, not LLM guessing), General Chat |
| O-2 | Workflow: raw prompt -> routing node (structured, Pydantic-validated output) -> selected skill node(s) get the skill name(s) + the original prompt -> final response |
| O-3 | Up to 2 simultaneous skills per prompt; the combination strategy is the candidate's decision and must be explained |
| O-4 | A defined fallback when the prompt matches no skill or is ambiguous; explain it |
| O-5 | Persian (Farsi) must work for routing and output |
| O-6 | Free-tier provider only (OpenRouter), model <= 35B parameters; state model and parameter count |
| O-7 | LangGraph graph (at least routing node + skill execution nodes); CLI interface only |
| O-8 | Out of scope: auth, database/persistence, memory across requests, deployment/scaling, FastAPI, more than 4 skills, more than 2 skills per prompt |
| O-9 | README: run instructions, graph architecture and decisions, per-skill prompt engineering, multi-skill and fallback handling, Persian handling, limitations, assumptions, AI-usage disclosure, provider/model |
| O-10 | A 10-15 prompt evaluation set with routing accuracy |
| O-11 | At least one before/after prompt-engineering example |
| O-12 | Bonus: clean git history (feature branches, descriptive incremental commits) |

## Working rules (kept from the brief and the author's instructions)

- Do not invent measurements: evaluation numbers must come from a real run; say so when something was not run.
- Never commit API keys; configuration comes from `.env` (`.env.example` has placeholders).
- Keep the code small and readable; no features outside the brief (synthetic skills live only in the simulation).
- Prompts live in `app/prompts/` (one file per skill) so they can be diffed.
