# 03 — Evaluate the produced output

**As** the eval author (who owns quality for a workflow)
**I want** the eval engine to take the output the workflow produced and grade
it against my suite's golden cases with the judge model
**so that** each run yields a per-case pass/fail I can trust, based on the
same evidence the workflow had.

## Context

This is the engine — what runs when story 02's handler fires. It reuses the
mechanics of `agentic-evals-service` (golden cases + LLM-as-judge +
per-dimension thresholds), adapted to the Ark world: instead of calling a
target application over HTTP to *produce* an answer, the engine **reads an
output the workflow has already produced** and grades it.

For Milestone 1 the output is a **file on the file-gateway volume** — the same
place the KYC workflow already writes it (e.g.
`.../intermediate/inquiry_information.json`). The engine reads that file, runs
each golden case against it, and asks the judge model (the Ark `Model` named in
the suite) to score the output against the suite's judge prompts.

The judge's own pass/fail verdict is **not trusted directly**: the engine
recomputes pass/fail from the per-dimension scores against the suite's
thresholds — the same discipline `agentic-evals-service` uses — so grading is
deterministic given the scores.

### How a case targets the output — the pyramid inside one file

The produced output is a structured document, so a golden case does **not**
grade "the whole file" as one blob. Following the strategy's pyramid (catch
each failure at the cheapest level that can see it), each case targets a
**slice** of the output and declares **how** to check it:

| Check type | Level | Verifies | Uses the judge? |
|------------|-------|----------|-----------------|
| `structural` | L1 | shape/contract: a field exists, schema valid, a value equals a literal like `_Pending_` | no — deterministic |
| `exact` | L2 | an extracted value equals the golden expected value | no — deterministic |
| `regex` | L2 | a value contains a substring or matches a simple pattern | no — deterministic |
| `schema` | L2 | a value matches a JSON Schema (type/enum/pattern/range/array/nested) | no — deterministic |
| `judge` | L3 | free-text quality: faithfulness to the evidence, completeness, tone | yes — LLM-as-judge |

So `structural` and `exact` cases cost nothing and never flake; only `judge`
cases invoke the model. A suite's pass rate is then a meaningful mix of cheap
deterministic checks and judged quality, and a failure names the specific
slice and check that failed rather than a vague "the file scored low".

## Acceptance criteria

_Observable, testable conditions. Each must be traceable to something the
implementation does — this is the contract we check the build against._

- [ ] The engine reads the workflow's produced output from the **file-gateway
      volume**, at the path passed by the handler (story 02), without
      re-running the workflow.
- [ ] Each golden case targets a **slice** of the output (e.g. a JSONPath into
      the produced file, or the whole document) and declares a **check type**:
      `structural` (L1), `exact` (L2), or `judge` (L3).
- [ ] `structural` and `exact` cases are graded **deterministically, without
      invoking the judge model**; only `judge` cases call the model.
- [ ] For each `judge` case, the engine grades the slice with the **judge
      model named in the suite**, using the suite's judge prompts (story 01).
- [ ] The judge returns scores matching the suite's judge **schema**; a
      response that does not match is retried, and a persistent mismatch is
      recorded as a case error, not a silent pass.
- [ ] Per-case **pass/fail is recomputed by the engine** from the dimension
      scores against the suite's thresholds — the judge's own overall verdict
      is not trusted on its own.
- [ ] `judge` cases score the slice against the **evidence available to the
      workflow** (the grounding the case provides), so groundedness/
      hallucination are judged fairly, not against outside knowledge.
- [ ] A failing case names **which slice and which check** failed (e.g. `exact`
      on `$...Company Name`: expected X, got Y), not just "failed".
- [ ] If the output file is **missing or unreadable**, the run reports a clear
      error (nothing to evaluate), distinct from "evaluated and failed".
- [ ] The judge model is invoked by **creating an Ark `Query` against the
      judge `Model`** named in the suite — so judge calls are traced in
      Langfuse like any other model call, with no separately configured
      gateway.

## Decisions (resolved)

- **Judge invocation**: the engine grades a `judge` case by creating an **Ark
  `Query`** against the judge `Model` named in the suite (not a directly
  configured gateway). This is Ark-native and makes judge calls appear in
  Langfuse alongside the workflow's own model calls.
- **Case ↔ output shape**: a case targets a **slice** of the output and
  declares a **check type** — `structural` (L1), `exact` (L2), or `judge`
  (L3) — so the engine only spends the LLM on what genuinely needs judgement,
  per the strategy pyramid. Making this understandable to future authors is
  owned by story 06 (onboarding).

## Out of scope

- Aggregating the per-case results into a pass rate and report — story 04.
- Acting on the result (threshold gate, alert, retrigger) — story 05.
- Reading the output from anywhere other than the file-gateway volume (e.g. a
  Query's `status.response`) — deferred; Milestone 1 is file-based.
- Multiple judge models / judge panels — one judge per suite.

## Open questions

_None._ (Story-01 scope is resolved: one suite per workflow; the engine is
pointed at the workflow's output(s), and cases target them via their slices.)
