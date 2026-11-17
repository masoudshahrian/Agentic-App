# Interviewer's clarifications (essential requirements)

Provided by the company's interviewer after the original brief (relayed by the candidate as a voice
explanation, then written down as a prompt). Each requirement has an ID used by the compliance matrix
in [README.md](README.md#requirement-compliance-matrix).

## I-1 Dynamic, extensible multi-skill architecture
The skill count may grow from 4 to 10, 20 or more. Adding a skill must not require editing the router's
internal logic, adding hard-coded branches or growing the main graph.
- I-1.1 Skills are independent and follow a common interface/contract.
- I-1.2 Registration and discovery are centralised; adding a skill needs minimal changes.
- I-1.3 The router discovers skills dynamically via metadata, not hard-coded descriptions.
- I-1.4 Metadata includes: unique id, name, description, supported input types, supported operations,
  execution handler, routing examples.
- I-1.5 Skill definitions are validated at registration; duplicate ids are rejected.
- I-1.6 Skill-specific details are isolated from the routing component.
- I-1.7 Initially expose EXACTLY the four required skills; no extra user-facing demo skills.

## I-2 Context-explosion prevention (major challenge)
Sending every skill's description, instructions, examples and full prompt to the router on every request
is not acceptable.
- I-2.1 Stage 1: lightweight discovery over compact metadata; identify a small candidate set; no full instructions.
- I-2.2 Stage 2: focused selection over the shortlisted metadata only; select up to two skills; validate ids.
- I-2.3 Stage 3: load and execute only the selected skills; pass the original prompt and explicitly required
  intermediate output; do not expose unrelated prompts.
- I-2.4 The router never receives full skill prompts; prompts are loaded lazily; compact metadata.
- I-2.5 No unnecessary vector DB or external infrastructure for the prototype.
- I-2.6 Document the context behaviour as the number of skills grows.

## I-3 Multi-skill selection and execution
- I-3.1 Select and execute up to two skills; reject invalid ids; prevent duplicates; enforce the maximum.
- I-3.2 No matching skill -> documented error/fallback policy; reconcile with General Chat and the original
  fallback: greetings -> General Chat; requests chat cannot handle -> clear unsupported response; ambiguous ->
  clarification; never silently run an unrelated skill.
- I-3.3 Parallel vs sequential decided from actual dependencies; explained in the architecture documentation.

## I-4 User-query and routing documentation
Document the query categories (direct, natural-language, Persian, English, multi-intent, implicit,
ambiguous, unsupported, multi-operation) with examples; explain how the prompt enters, how skills are
represented, how candidates are found, how selection is validated, how skills execute and how results
return; document the assumptions.

## I-5 Clean code and maintainable structure
Separation of concerns, modularity, single responsibility, low coupling, clear interfaces, typed
definitions; avoid a monolithic main.py, hard-coded skill branches, duplicated prompts, overengineering.

## I-6 GitHub repository, branching, history
Public repository is a deliverable: professional layout, meaningful incremental commits, feature branches,
clean main, README, no secrets, `.env.example`. **Do not create a remote or push without explicit authorisation.**

## I-7 AI-assisted development disclosure, specification-driven workflow
AI assistants are allowed if disclosed. Maintain PROJECT_SPEC, INTERVIEWER_REQUIREMENTS, ARCHITECTURE,
IMPLEMENTATION_PLAN, CLAUDE.md, AI_USAGE describing the real implementation; AI_USAGE must state which tasks
were AI-assisted, which decisions were reviewed and how code was tested.

## I-8 Additional evaluation tests
Tests for: new skill without router edits; duplicate ids; invalid definitions; discovery via registry;
selection from a larger registry; unselected full prompts never loaded; only selected prompts reach
execution; max two skills; unknown ids; no matching skill; Persian and English; ambiguous requests;
sequential dependent execution; parallel independent execution. Plus a scalability simulation (50-100+
synthetic skills, not added to the app) measuring registered / candidate / selected counts, full prompts
loaded, approximate routing-context size and whether unselected prompts were accessed - no fabricated numbers.

## I-9 Final architecture review
Independent review against the points above; fix defects; README section "Scalable Skill Registry and
Context Management"; a compliance matrix mapping every original requirement and every clarification to
module, test and documentation section.
