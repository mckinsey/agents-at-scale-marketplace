# 06 — The eval author understands how to write a suite

**As** a first-time eval author (someone who has never used this add-on)
**I want** to understand the suite model — slices, check types, thresholds,
judge prompts — quickly and by example
**so that** I can write a correct suite for my own workflow without reading
the engine's source or guessing.

## Context

The suite model (story 01) and the slice + check-type model (story 03) are
powerful but introduce concepts an author must grasp before writing the first
case: *where* to look (slice), *how* to check it (`structural` / `exact` /
`judge`), and *what* to expect. Left unexplained, the add-on is correct but
unadopted.

This story owns **understandability**. The position taken (during design) is
that comprehension comes from onboarding — a copyable example, self-describing
errors, and one small table — not from simplifying the model down to
"just judge everything", which would trade easy authoring for uninterpretable
results.

## Acceptance criteria

_Observable, testable conditions. Each must be traceable to something the
implementation does — this is the contract we check the build against._

- [ ] The add-on ships a **reference suite** (a complete, working
      `dataset.json` + judge prompts) covering one `structural`, one `exact`,
      and one `judge` case, that an author copies and edits — the way
      `agentic-evals-service` ships `example_echo`.
- [ ] The reference suite runs end to end against a **bundled example output**
      with no real workflow, so an author sees a green run before touching
      their own product.
- [ ] The suite documentation includes a **one-glance table** mapping intent →
      check type ("verify a field exists" → `structural`; "value equals X" →
      `exact`; "text is faithful/quality" → `judge`).
- [ ] Errors are **didactic**: an unknown check type, a slice that resolves to
      nothing in the output, or a `judge` case missing its rubric produces a
      message that names the problem and the allowed options — not a stack
      trace or a silent skip.
- [ ] A report line for a failed case is **self-explanatory** (names the slice,
      the check type, expected vs actual) so the author learns the model by
      seeing results, not only by reading docs (ties to story 04).
- [ ] A **validation/`doctor`-style command** tells the author whether their
      suite is well-formed (dataset parses, judge model resolves, prompts
      reference existing schemas) before any run — mirroring
      `agentic-evals-service`'s conformance check.

## Decisions (resolved)

- **Where the docs live**: in the Evals package `README` (the service root
  `README.md`), following how other marketplace items document themselves. The
  intent→check-type table and the pointer to the reference suite live there.

## Out of scope

- A UI or visual editor for suites (deferred with the rest of the UI).
- Auto-generating suites from a workflow (an AI-assisted authoring flow, like
  `agentic-evals-service`'s customization tooling) — a later evolution.
- Teaching the workflow owner how to add the `onExit` hook — that is part of
  story 02's material, not this one.

## Open questions

_None._
