# Scalability simulation (synthetic skills, stub router - not a real LLM)

- Run at (UTC): 2026-11-16T13:46:51+00:00
- 20 queries per registry size; vocabulary: 25 nouns x 8 verbs.
- `approx tokens` = characters / 4 (an approximation, not a tokenizer count).
- `naive` = router prompt if EVERY skill's metadata and full prompt were injected (computed from the real strings).
- Shortlist/selection rates are measured on synthetic data written by the same author: a sanity check, not a benchmark.

| Registered (incl. 1 fallback) | Avg candidates | Avg selected | Full prompts loaded before execution (max) | Avg loaded after execution | Unselected prompt accessed | Avg routing context (chars / ~tokens) | Naive context (chars / ~tokens) | Reduction | Target in shortlist | Strategy |
|---|---|---|---|---|---|---|---|---|---|---|
| 11 | 6.0 | 1.0 | 0 | 1.0 | no | 3855 / ~964 | 42531 / ~10632 | 11.0x | 100% | lexical |
| 51 | 6.0 | 1.0 | 0 | 1.0 | no | 3879 / ~970 | 188682 / ~47170 | 48.6x | 100% | lexical |
| 101 | 6.0 | 1.0 | 0 | 1.0 | no | 3876 / ~969 | 371285 / ~92821 | 95.8x | 100% | lexical |
| 201 | 6.0 | 1.0 | 0 | 1.0 | no | 3877 / ~969 | 736491 / ~184122 | 190.0x | 100% | lexical |
