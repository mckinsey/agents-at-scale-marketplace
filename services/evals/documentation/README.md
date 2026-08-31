# Evals — User Stories

This folder captures the product intent for the Evals add-on as small,
self-contained user stories, **authored by the Product Owner of the
marketplace Evals project**. One story per file. Each is deliberately narrow:
a single capability, framed around the person who benefits from it.

Their purpose is to be the **acceptance contract we validate the design and
implementation against — before any code is written**. If a story's
acceptance criteria cannot be traced to something the implementation does,
either the story or the implementation is wrong. We define and refine these
interactively here.

## Convention

- One story per file, named `NN-short-slug.md` (e.g. `01-run-eval-after-workflow.md`).
- Each file follows the template in [`_template.md`](_template.md).
- Stories are written in English (per project convention).

## Scope — Milestone 1

Trigger an evaluation as the final step of a successful Ark workflow, evaluate
the file it produced against a golden dataset with an LLM-as-judge, and report
a pass rate against a threshold. No custom CRD, no UI — configuration via
`ConfigMap`, files edited in code.

## Guides

- [`dataset-guide.md`](dataset-guide.md) — step-by-step reference for writing a
  suite's `dataset.json` (every field, the `check` enum, the slice syntax, an
  end-to-end example). Written for both human authors and AI agents.
- [`evolving-the-framework.md`](evolving-the-framework.md) — what the current
  literature and SOTA frameworks say about agent evals (judge panels, trajectory
  evaluation, pass@k/pass^k, error bars, dataset growth), each mapped to a
  concrete next step for this engine, with citations. The forward-looking design
  note beyond Milestone 1.

## Planned stories (Milestone 1)

1. Configure an eval suite — golden dataset, threshold, judge model.
2. Trigger the eval when a workflow finishes (onExit hook).
3. Evaluate the output the workflow produced (the file it wrote).
4. Produce a report with a pass rate.
5. Gate on the threshold — surface a below-threshold result for a human decision.
6. Onboarding — the eval author understands how to write a suite.

## Index

| # | Story | Status |
|---|-------|--------|
| 01 | [Configure an eval suite](01-configure-eval-suite.md) | done |
| 02 | [Trigger the eval after a workflow (onExit hook)](02-trigger-eval-after-workflow.md) | done |
| 03 | [Evaluate the produced output](03-evaluate-produced-output.md) | done |
| 04 | [Report the pass rate](04-report-pass-rate.md) | done |
| 05 | [Gate on the threshold (human-in-the-loop)](05-gate-on-threshold.md) | done |
| 06 | [The eval author understands how to write a suite](06-eval-author-onboarding.md) | done |
