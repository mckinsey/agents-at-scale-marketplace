# 04 — Report the pass rate

**As** the reviewer (the person who reads eval results and owns the decision)
**I want** each eval run to produce a readable report with an overall pass
rate and a per-case breakdown
**so that** I can see at a glance how good a workflow run's output was, and
drill into exactly which cases failed and why.

## Context

This is the visible output of the milestone — the log/report the whole feature
exists to produce. When the eval engine (story 03) has graded every golden
case, it aggregates the per-case results into one report: an overall **pass
rate** (share of cases that passed), and a per-case list showing what each case
checked and how it scored.

For Milestone 1 the report is a **single artifact: a human-readable Markdown
report**, not a UI and not a Kubernetes object. It is written next to the
output it graded (on the file-gateway volume) and echoed to the handler log, so
it can be read after the fact with the same tools the KYC workflow's outputs
are already read with. It reports; it does not decide — acting on the pass rate
is story 05.

A report is a per-run *result*, not configuration, so it is deliberately an
artifact rather than a `ConfigMap`/CRD (which would accumulate one object per
run with no natural lifecycle). A structured/machine-readable format and a
run-over-run history are possible later; Milestone 1 keeps one Markdown file.

The report is also a teaching surface (story 06): a failed line names the
slice, the check type, and expected-vs-actual, so a reviewer understands the
verdict without reading the engine.

## Acceptance criteria

_Observable, testable conditions. Each must be traceable to something the
implementation does — this is the contract we check the build against._

- [ ] The report states an overall **pass rate** for the run (passed cases /
      total cases), against the suite's threshold (story 01) — shown, not
      enforced.
- [ ] The report lists **every case** with its id, the slice it targeted, its
      check type (`structural` / `exact` / `judge`), and pass/fail.
- [ ] A **failing case** shows why it failed: for `structural`/`exact`, the
      expected vs actual value; for `judge`, the per-dimension scores, the
      threshold they missed, and the judge's rationale.
- [ ] For `judge` cases the report includes the **judge's rationale**, not just
      a number, so a low score is explainable.
- [ ] The report distinguishes **case errors** (judge schema mismatch, missing
      output file) from **case failures** (evaluated and scored below bar), so
      "the eval broke" is never read as "the output was bad".
- [ ] The report is written as a **single Markdown artifact** on the
      file-gateway volume (and echoed to the handler log), readable after the
      run — not only printed to stdout and lost, and not stored as a k8s object.
- [ ] The report records **which suite and which judge model** produced it, and
      is tied to the workflow run that triggered it, so a result is traceable
      to its inputs.

## Decisions (resolved)

- **Format and location**: a single **Markdown** report written to the
  file-gateway volume (next to the graded output) and echoed to the handler
  log. No separate JSON/YAML, no Kubernetes object — a per-run result is an
  artifact, not configuration. Machine-readable output and history are deferred.

## Out of scope

- Acting on the pass rate — gate, alert, retrigger, human-in-the-loop (story
  05). This story is report-only.
- A dashboard/UI rendering of the report (deferred with the rest of the UI).
- Historical trend / run-over-run comparison and regression detection
  (a later evolution; `agentic-evals-service` has this, Milestone 1 does not).
- A machine-readable (JSON/YAML) report format (deferred; Milestone 1 is
  Markdown only).
- Writing eval scores back onto the Langfuse trace as Langfuse `scores`
  (the "Ruolo B" integration) — a natural next step, but deferred; note that
  judge calls themselves are already traced via story 03's Ark `Query`.

## Open questions

_None._ (Story-01 scope is resolved: one suite per workflow → one report per
workflow run, with a section per evaluated output when there is more than one.)
