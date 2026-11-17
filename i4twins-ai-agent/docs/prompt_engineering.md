# Prompt engineering

Every skill has its own file in `app/prompts/` (`router.txt`, `summarizer.txt`,
`translator.txt`, `calculator.txt`, `general_chat.txt`). The first line `ROLE: <name>` is
only a marker used by the test fake. All prompts share these principles:

- explicit output contract ("output ONLY the summary", "ONLY a JSON object");
- the user's text is **data** inside tags (`<original_request>`, `<previous_step_output>`),
  with an instruction to ignore instructions found inside it (prompt-injection hygiene);
- the same prompt handles English and Persian, with explicit Persian typography rules
  (natural Persian, ZWNJ half-spaces, Persian punctuation);
- each skill ignores parts of the request that belong to another skill (needed for parallel
  two-skill prompts, where both skills see the whole request).

## Summarizer: v1 -> final

**v1**

```
Summarize the following text.
```

**Final**: see `app/prompts/summarizer.txt`.

| Problem expected with v1 | Change in the final prompt | How to check |
|---|---|---|
| Model adds background knowledge or opinions | "Never add facts, opinions or interpretation"; keep names, numbers, dates exactly | Compare numbers/names in the summary to the source (manual review of `--full` outputs, or LLM-judge for factual consistency) |
| Unpredictable length (1 line or 3 paragraphs) | Default length rule + honour "one sentence", "3 bullet points", "short", "detailed" | Count sentences/bullets against the request |
| Persian text summarized in English (or the reverse) | "Write in the language the user asked for, otherwise the source language" | Check script of the output |
| Preface "Here is the summary:" breaks chaining into the translator | "Output ONLY the summary" | Output starts with content |
| Request containing "and translate it" makes the summarizer translate too | Ignore other tasks in the request; they are handled elsewhere | In a two-skill prompt the first step output stays in the source language |
| Missing text -> hallucinated summary | "If there is no text, ask for it" | Prompt "Summarize this." |

**Honesty note:** the v1 -> final changes above are derived from known failure modes; the
repository does not contain recorded outputs of v1 from a live model (only the router prompt was compared live). To produce that evidence, run the same prompt with both versions
(put v1 in a temporary file, call `summarizer.run` with it) and paste the two outputs here.

## Router: v1 -> final (with a reproducible measurement)

The router prompt is now **skill-agnostic**: `app/prompts/router.txt` holds only generic rules and the output
schema, and `<<CANDIDATES>>` is replaced at request time by one compact line per *shortlisted* skill built from
its metadata (`id`, name, description, operations, input types, `routing_hint`, routing examples, `[fallback]` /
`[chainable]` tags). Skill-specific boundary rules (for example "numbers inside a text to summarize are not a
calculation") moved into each skill's `routing_hint`, and few-shot examples come from each skill's
`routing_examples`. Result: the prompt size depends on the number of candidates (<= 6), not on the number of
registered skills, and adding a skill needs no prompt edit.

**v1** (`evaluation/router_v1_naive.txt`): "pick the skills from this list" + the JSON shape, no rules.
**Final**: `router.txt` (10 generic rules: meaning over language, 1-2 ids, hints, chaining only for chainable
skills, clarification, unsupported requests, injection hygiene, language code, confidence, short reasoning).

Both can be measured on the same fixed dataset (needs an API key):

```bash
python -m evaluation.evaluate --router-prompt evaluation/router_v1_naive.txt
python -m evaluation.evaluate
```

Results are written to `evaluation/results/live_router_v1_naive.md` and `live_router.md`.
**Measured 16 Nov 2026** with `google/gemma-4-31b-it` (OpenRouter): both the final router prompt and the naive v1 prompt
scored 100% on all metrics (15/15 exact skill sets), so this dataset does not separate them. The final prompt's
advantage is structural (skill-agnostic, candidate lines built from metadata), not shown by accuracy here. The prior hand-written few-shot router prompt (before
the metadata-driven redesign) was also never measured live, so there is no live before/after for it.
