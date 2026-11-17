# User query categories and routing

How a prompt is handled: the raw text enters the graph unchanged -> **discover** shortlists skills from compact
metadata -> **router** (LLM, shortlist only) returns a validated `RoutingDecision` -> **execute_skill** runs the
selected skill(s) with the original prompt (plus the previous output for a chain) -> **aggregator** builds the answer.

"Expected routing" below is the **design intent**, enforced by validation and covered by scripted tests; how
well the live LLM follows it was measured once on the 15-prompt dataset (README section 8: 15/15). The keyword baseline column shows what the
deterministic fallback router actually returns (checked by `tests/test_router.py::test_heuristic_routes`
and the offline evaluation).

| Category | Example | Expected routing | Keyword fallback | Notes |
|---|---|---|---|---|
| Direct skill request | "Summarize this article: ..." | `summarizer` | summarizer | Names the skill |
| Natural-language request | "Can you make this paragraph shorter? ..." | `summarizer` | general_chat (no keyword) | Needs the LLM; implicit wording |
| English | "What is 245 * 36?" | `calculator` | calculator | |
| Persian | "حاصل ۲۵ ضربدر ۴۸ چیست؟" | `calculator`, language `fa`, Persian-digit answer | calculator | Persian digits/words |
| Persian instruction, English text | "Translate to Persian: Good morning" | `translator` | translator | Language of instruction != language of content |
| Multi-intent, dependent | "Summarize this and translate the summary to English: ..." | `summarizer` -> `translator`, sequential | same | Second skill is `accepts_previous_output` |
| Multi-intent, independent | "Translate 'hi' into French and calculate 25*48" | `translator` + `calculator`, parallel | same | Labelled sections |
| Multiple operations, one skill | "Translate this into French and German" | `translator` once | translator | One skill can do several operations; the skill's prompt handles it |
| Implicit skill requirement | "How do you say 'thank you' in French?" | `translator` | translator (keyword "in french") | Matches translator's routing example |
| Numbers inside a text | "Summarize: revenue grew from 2.5 to 4.1 million ..." | `summarizer` (not calculator) | summarizer | Hint on the summarizer |
| Conversation / general knowledge | "Hello!", "What is a prime number?" | `general_chat` | general_chat | Fallback skill; not an error |
| Ambiguous | "Translate this." / "ترجمه کن" | clarification question, no skill runs | clarification | Also when confidence < 0.4 |
| Unsupported | "Book me a flight to Tehran" | `unsupported_request`, clear message, no skill runs | general_chat (cannot detect) | Needs an action no skill provides |
| Invalid LLM output | (malformed JSON / unknown id / 3 skills) | retry once, then keyword router | - | Never silently accepted |

## Assumptions behind the supported query types

- One request = one independent prompt; no conversation history.
- Skills are selected by meaning, not by language; instructions and content may be in different languages.
- At most two skills per request; a pair is either a dependency chain or two independent tasks.
- The target language for translation can be inferred (Persian -> English, otherwise -> Persian) when not stated.
- "Needs an action or live data" (booking, sending, browsing, files) is unsupported, not general chat.
- With a large registry, an implicit request that shares no vocabulary with any skill is found only through the
  LLM-shortlist path; good skill descriptions and keywords are part of adding a skill.
