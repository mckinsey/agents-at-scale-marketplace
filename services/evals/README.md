# Evals

An evaluation add-on for Ark agentic workflows. Runs a golden-dataset,
LLM-as-judge evaluation over the output a workflow produces, and reports a
pass rate against a configurable threshold.

> **Status:** planning / exploration. This folder currently holds only the
> product documentation (user stories under `documentation/`). No chart,
> image, or code has been written yet.

## What it will do

- Trigger an evaluation as a final step of an Ark/Argo workflow, once the
  workflow completes successfully.
- Read the output the workflow produced (Milestone 1: a file on the
  file-gateway volume), compare it against curated golden cases, and score it
  with an LLM-as-judge (quality + hallucination).
- Produce a log/report with a **pass rate** and, when the pass rate falls
  below a configured **threshold**, surface it for a human-in-the-loop
  decision (auto-retrigger is a later extension).

## Approach

The evaluation engine reuses the model and mechanics of the internal
`agentic-evals-service` (golden dataset + judge + thresholds + report),
adapted to the Ark world: instead of calling a target application over HTTP,
it evaluates the output an Ark workflow has already produced.

Configuration (which Ark `Model` is the judge, the pass threshold, and the
golden dataset) lives in a `ConfigMap` for Milestone 1 — files edited in code
and applied with `kubectl`, no custom CRD and no UI yet. A CRD and a UI are
possible later evolutions, not part of the first milestone.

## Documentation

Product intent is captured as small user stories under
[`documentation/`](documentation/). Start with
[`documentation/README.md`](documentation/README.md) for the index.
