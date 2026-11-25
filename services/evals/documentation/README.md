# Evals — documentation

Documentation for the Evals add-on, in three parts:

- **Guides** — how-to references for using the add-on.
- **User stories** — the acceptance contract the design and implementation are
  validated against.
- **Design notes** — forward-looking, literature-grounded direction.

For an overview, install, and how to wire the eval into a workflow, start at the
service [`README`](../README.md).

## Guides

- [`dataset-guide.md`](dataset-guide.md) — step-by-step reference for writing a
  suite's `dataset.json`: every case field, the `check` types, the slice
  syntax, and an end-to-end example. **This is the canonical reference for the
  check types** — other docs link here rather than restating them. Written for
  both human authors and AI agents.

## Design notes

- [`evolving-the-framework.md`](evolving-the-framework.md) — what current
  literature and SOTA frameworks say about agent evals (judge panels, trajectory
  evaluation, pass@k/pass^k, error bars, dataset growth), each mapped to a
  concrete next step for this engine, with citations. Beyond Milestone 1.

## User stories

The product intent for the Evals add-on, captured by the Product Owner as small,
self-contained user stories — one capability per file, framed around the person
who benefits. Their purpose is to be the **acceptance contract validated against
the design and implementation before any code**: if a story's acceptance
criteria cannot be traced to something the implementation does, either the story
or the implementation is wrong.

They are kept as authored (a pre-implementation snapshot of the agreed design);
`_template.md` is the shape a new story follows.

**Scope — Milestone 1:** trigger an evaluation when an Ark workflow finishes,
evaluate the file it produced against a golden dataset with an LLM-as-judge, and
report a pass rate against a threshold. No custom CRD, no UI — configuration via
`ConfigMap`, files edited in code.

| # | Story | Status |
|---|-------|--------|
| 01 | [Configure an eval suite](user-stories/01-configure-eval-suite.md) | done |
| 02 | [Trigger the eval after a workflow (onExit hook)](user-stories/02-trigger-eval-after-workflow.md) | done |
| 03 | [Evaluate the produced output](user-stories/03-evaluate-produced-output.md) | done |
| 04 | [Report the pass rate](user-stories/04-report-pass-rate.md) | done |
| 05 | [Gate on the threshold (human-in-the-loop)](user-stories/05-gate-on-threshold.md) | done |
| 06 | [The eval author understands how to write a suite](user-stories/06-eval-author-onboarding.md) | done |
