# Evals

An evaluation add-on for Ark agentic workflows. It grades the output a workflow
produces against a golden dataset with an LLM-as-judge, and writes a Markdown
report with a pass rate against a configurable threshold. It is triggered from
the workflow's `onExit` hook, so the workflow stays focused on its own job.

## How it works

```
workflow finishes ──onExit──▶ eval WorkflowTemplate ──▶ ark-evals engine
                                                            │
   reads produced output (file-gateway) ◀───────────────────┤
   grades each case (structural / exact / judge)             │
   judge = an Ark Query against your judge Model ◀───────────┤
   writes a Markdown report + pass rate ─────────────────────▶ file-gateway
```

- **Report-only (Milestone 1):** a below-threshold result is reported for a
  human to act on; it does not block or retrigger the workflow.
- **Judge via Ark:** the judge is an existing Ark `Model`, called by creating an
  Ark `Query`, so judge calls are traced in Langfuse like any other model call.

## Writing a suite

A suite is a folder (see `chart/files/kyc-profile-init` for the reference):

```
<suite>/suite.json     # judge Model name, pass threshold, per-dimension thresholds
<suite>/dataset.json   # the golden cases
<suite>/judges/quality.prompt.txt    # the rubric the judge scores against
<suite>/judges/quality.schema.json   # the JSON shape the judge must return
```

Each case targets a **slice** of the output and declares a **check type**. Pick
the cheapest check that can see the failure — deterministic checks
(`structural`, `exact`, `regex`, `schema`) cost nothing and never flake; only
`judge` calls the model. The full reference — every check type, the slice
syntax, and an end-to-end example — is in
[`documentation/dataset-guide.md`](documentation/dataset-guide.md).

Validate a suite before running it (no model calls):

```bash
python -m ark_evals validate --suite-dir <mounted-suite-dir>
```

## Install

```bash
# Build the engine image (OrbStack shares the docker daemon with the cluster).
docker build -t ark-evals-engine:0.1.0 engine/

# Install the add-on: eval WorkflowTemplate, runner ServiceAccount + RBAC,
# and the reference-suite ConfigMap.
helm install evals ./chart -n default
```

Apply your own suite folder as a ConfigMap:

```bash
./chart/files/apply-suite.sh <suite-dir> default
```

## Trigger it from a workflow

Add an `onExit` hook to the workflow you want evaluated (a one-line reference
plus a small handler). See the install `NOTES.txt` for the exact snippet; in
short:

```yaml
onExit: eval-onexit
templates:
  - name: eval-onexit
    steps:
      - - name: evaluate
          when: "{{workflow.status}} == Succeeded"
          templateRef: { name: eval-run, template: evaluate }
          arguments:
            parameters:
              - { name: suite-name,    value: kyc-profile-init }
              - { name: output-key,    value: <produced file key> }
              - { name: report-key,    value: <report destination key> }
              - { name: workflow-name, value: "{{workflow.name}}" }
```

## Documentation

Product intent and the acceptance contract for Milestone 1 live as user stories
under [`documentation/`](documentation/).

> **Status:** Milestone 1 — trigger an eval on workflow completion, grade a
> produced file, report a pass rate. No UI, no custom CRD, report-only.
