# 05 — Gate on the threshold (human-in-the-loop)

**As** the reviewer (the person who owns the decision about a workflow run)
**I want** an eval whose pass rate falls below the suite's threshold to be
clearly flagged as below bar
**so that** I can decide what to do about it — without the system silently
accepting a bad run or acting on its own.

## Context

The suite declares a pass threshold (story 01); the report states the pass rate
(story 04). This story is the seam where the two meet: the Markdown report
compares the pass rate to the threshold, gives a clear verdict, and accounts
for what passed and what did not, so a human can read it and decide. For
Milestone 1 the report *is* the signal — there is no separate flag or alert.

For Milestone 1 the gate is **advisory, not enforced**: the eval observes,
compares against the threshold, and flags — it does **not** block the workflow,
change its status, or retrigger anything (as fixed in story 02). The decision,
and any action, stays with the human. Automatic responses (block, auto-retrigger,
alerting) are deliberately deferred: they are the more dangerous, higher-trust
behaviours, and they only make sense once the eval itself is trusted.

## Acceptance criteria

_Observable, testable conditions. Each must be traceable to something the
implementation does — this is the contract we check the build against._

- [ ] The Markdown report states the **threshold used** and the run's **pass
      rate**, and an unambiguous **PASS / BELOW-THRESHOLD** verdict comparing
      the two — not just a number the reader has to compare themselves.
- [ ] The report gives an account of **what was evaluated**: each case, the
      slice it targeted, its check type, and **which passed and which did not**.
- [ ] Below threshold does **not** change the workflow run's status, block it,
      or retrigger it — the eval remains report-only (consistent with story 02).
- [ ] The verdict is computed against the **suite's own threshold** (per-suite,
      per story 01), not a single global value.
- [ ] The report distinguishes **below-threshold** (evaluated, scored under
      bar) from **could-not-evaluate** (case errors / missing output, per story
      03), so a broken eval is never mistaken for a failing output.

## Decisions (resolved)

- **Signalling is the Markdown report only.** For Milestone 1 the below-threshold
  condition is conveyed by the report stating the threshold, the pass rate, the
  PASS/BELOW-THRESHOLD verdict, and the per-case pass/fail account — nothing
  more. No special banner, distinct log level, or Argo node message; richer
  prominence comes later with the automatic-action work.

## Out of scope

- **Automatic action** on a below-threshold result — blocking the workflow,
  auto-retriggering it, paging/alerting. Deferred to a later milestone; this
  story only reports for a human.
- A workflow-status or exit-code gate (the `--fail-under`-style hard gate that
  `agentic-evals-service` still lacks) — deferred with the automatic actions.
- Routing/ownership of the human decision (who gets notified, escalation
  paths) — an operating-model concern, out of scope for Milestone 1.
- Any UI affordance for acting on the result (deferred with the rest of the UI).
- Any signalling beyond the Markdown report (banner, log level, node message).

## Open questions

_None._
