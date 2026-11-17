# Routing evaluation — deterministic keyword router (no LLM)

- Run at (UTC): 2026-11-16T13:46:39+00:00
- Prompts: 15

| Metric | Value |
|---|---|
| Exact skill-set accuracy | 93.3% |
| Multi-skill detection accuracy (n=3) | 100.0% |
| Clarification decision accuracy | 100.0% |
| Unsupported-request decision accuracy | 93.3% |
| Persian routing accuracy (n=6) | 100.0% |

| Skill | Precision | Recall | F1 | Support |
|---|---|---|---|---|
| summarizer | 100.0% | 100.0% | 100.0% | 5 |
| translator | 100.0% | 100.0% | 100.0% | 7 |
| calculator | 100.0% | 100.0% | 100.0% | 3 |
| general_chat | 66.7% | 100.0% | 80.0% | 2 |

| # | Expected | Predicted | Clarify (exp/pred) | Unsupported (exp/pred) | OK |
|---|---|---|---|---|---|
| 1 | summarizer | summarizer | False/False | False/False | yes |
| 2 | translator | translator | False/False | False/False | yes |
| 3 | calculator | calculator | False/False | False/False | yes |
| 4 |  | general_chat | False/False | True/False | **NO** |
| 5 | summarizer | summarizer | False/False | False/False | yes |
| 6 | translator | translator | False/False | False/False | yes |
| 7 | calculator | calculator | False/False | False/False | yes |
| 8 | general_chat | general_chat | False/False | False/False | yes |
| 9 | summarizer, translator | summarizer, translator | False/False | False/False | yes |
| 10 | summarizer, translator | summarizer, translator | False/False | False/False | yes |
| 11 | translator, calculator | translator, calculator | False/False | False/False | yes |
| 12 | translator | translator | True/True | False/False | yes |
| 13 | translator | translator | True/True | False/False | yes |
| 14 | summarizer | summarizer | False/False | False/False | yes |
| 15 | general_chat | general_chat | False/False | False/False | yes |
