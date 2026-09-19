# 01 — Configure an eval suite

**As** the eval author (the person who owns quality for a workflow)
**I want** to declare what to evaluate — the golden dataset, the pass
threshold, and which Ark `Model` acts as the judge — in one place I edit and
apply
**so that** an evaluation can run against a known, versioned definition of
"good" without changing any code.

## Context

The eval suite is the definition of an evaluation for one workflow output. It
is the single artifact the eval author edits. It holds four things — the
golden dataset (the cases and their expected/graded outcome), the judge
prompts (the rubric the judge scores against), the pass threshold, and the
judge model reference. Everything downstream (the trigger, the engine, the
report) reads this one definition, so it is where the contract of an
evaluation lives.

The author edits it as plain files (no custom CRD, no UI in Milestone 1).
Because the evaluation runs as a container in the cluster, those files have to
reach the container without rebuilding an image — which is exactly what a
Kubernetes `ConfigMap` is for: the author writes a suite folder on disk, turns
it into a `ConfigMap` with `kubectl` (each file becomes one key), and the next
run picks it up. The `ConfigMap` lives in the **same namespace as the workflow**
it evaluates (`default` for the KYC demo), so the trigger can find it without
crossing namespaces.

### Suite structure

A suite is a folder on disk, materialized into one `ConfigMap`. The dataset is
a single JSON document; the judge prompts and their output schemas are
separate files so the author can edit the rubric directly:

```
<suite-name>/
├── suite.json                    # threshold, judge Model name, dataset + judge file refs
├── dataset.json                  # the golden cases (array of case objects)
└── judges/
    ├── quality.prompt.txt        # the quality rubric the judge scores against
    ├── quality.schema.json       # the JSON shape the quality judge must return
    ├── hallucination.prompt.txt  # the hallucination rubric (optional per case)
    └── hallucination.schema.json # the JSON shape the hallucination judge must return
```

`suite.json` is the entry point — it names the judge `Model`, sets the
threshold, and points at the dataset and judge files. Because `ConfigMap` keys
cannot contain `/`, the `judges/` files are flattened to dotted keys
(`judges.quality.prompt.txt`) when the folder is turned into the `ConfigMap`;
on disk the author keeps the readable folder layout above.

## Acceptance criteria

_Observable, testable conditions. Each must be traceable to something the
implementation does — this is the contract we check the build against._

- [ ] An eval suite is a folder of plain files, materialized into a single
      `ConfigMap` with `kubectl`, with no code change and no image rebuild
      required.
- [ ] The suite's `ConfigMap` lives in the **same namespace as the workflow**
      it evaluates (`default` for the KYC demo).
- [ ] The suite declares a **golden dataset** (`dataset.json`): a set of
      cases, each with an input identity, the expected outcome, and the
      grading dimensions to score.
- [ ] The suite carries its **judge prompts** as editable files
      (`judges/*.prompt.txt`) plus the JSON schema each judge must return
      (`judges/*.schema.json`), so the author writes the rubric directly — the
      engine does not hard-code it.
- [ ] The suite declares a **pass threshold** (a minimum acceptable pass
      rate) that the report is judged against.
- [ ] The suite declares which **Ark `Model`** is used as the judge, by name
      (reusing an existing Ark `Model`, not a new model definition).
- [ ] A suite is identified by a **name** that later stories reference (the
      trigger says "evaluate with suite X").
- [ ] A malformed suite (missing threshold, unknown judge model, unparseable
      dataset, judge prompt referencing a missing schema) is reported as a
      clear configuration error, not a silent partial run.

## Decisions (resolved)

- **Delivery mechanism**: a Kubernetes `ConfigMap`, one per suite.
- **Dataset format**: a single JSON document (`dataset.json`), not JSONL.
- **Judge prompts**: carried by the suite as editable files
  (`judges/*.prompt.txt` + `*.schema.json`); the engine does not hard-code the
  rubric.
- **Namespace**: the `ConfigMap` lives in the same namespace as the workflow
  it evaluates (`default` for the KYC demo).
- **Scope**: **one suite per workflow.** A suite grades the workflow it is
  attached to; when a workflow produces several outputs, the one suite's cases
  target them via their slices (story 03). This keeps one `onExit` reference
  (story 02) and one report (story 04) per workflow run.

## Out of scope

- Any UI for editing the suite (deferred; Milestone 1 is files + `kubectl`).
- A custom `EvalSuite` CRD (deferred; a `ConfigMap` is used for now).
- Auto-generating the golden dataset or judge prompts from the workflow.
- Multiple judges / judge panels — one judge model per suite for now.

## Open questions

_None._
