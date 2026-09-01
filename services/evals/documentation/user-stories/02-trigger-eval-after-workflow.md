# 02 — Trigger the eval after a workflow, via an onExit hook

**As** the workflow owner (the person who runs the agentic workflow)
**I want** the evaluation to run automatically when my workflow finishes,
without the evaluation logic living inside my workflow
**so that** every run is measured while my workflow stays focused on its own
job and the eval can evolve independently.

## Context

The evaluation is a **separate, reusable Argo template** — not a step mixed
into the workflow's functional steps. The workflow that produces the output
does not contain the eval logic; it only *references* the eval and lets Argo
run it on completion.

The mechanism is Argo's **`onExit` hook**. The workflow declares
`onExit: <eval-handler>` (one line in its `WorkflowTemplate`), and Argo runs
that handler when the workflow ends. The handler does a `templateRef` to the
standalone eval template, so the eval definition lives on its own and can be
reused by other workflows and re-run in isolation. `onExit` runs regardless of
outcome, so the handler itself checks `{{workflow.status}}` and only evaluates
when the workflow **Succeeded** — evaluating an output that was never produced
is meaningless.

This does require a one-line edit to the workflow being evaluated (the
`onExit:` reference). That is the accepted trade-off for Milestone 1: it keeps
the eval independent and reusable without introducing an external watcher
(Argo Events), which would be the only fully zero-touch option and is a heavier
dependency deferred to later.

## Acceptance criteria

_Observable, testable conditions. Each must be traceable to something the
implementation does — this is the contract we check the build against._

- [ ] The eval is defined as a **standalone Argo template**
      (`WorkflowTemplate` / `ClusterWorkflowTemplate`), independent of any
      workflow that uses it, and referenced via `templateRef`.
- [ ] A workflow triggers the eval by declaring **`onExit: <handler>`** — a
      single reference — not by embedding eval steps in its own step list.
- [ ] The eval only evaluates when the workflow **Succeeded** (the handler
      gates on `{{workflow.status}}`); on a failed/errored workflow it does not
      attempt to grade a missing output.
- [ ] The handler passes to the eval **which suite** to run, as a **literal
      suite name parameter** on the `onExit` reference, and **which output** to
      evaluate (the produced file's path) — neither hard-coded in the eval
      template, and no naming-convention inference.
- [ ] The eval run is visible as its own step/handler in the workflow run
      (`kubectl get workflow` / dashboard Workflow runs view), distinct from
      the workflow's functional steps.
- [ ] The same eval template can be referenced by more than one workflow
      without copying it.

## Decisions (resolved)

- **Suite selection**: a **literal suite name** passed as a parameter on the
  `onExit` reference — not derived by naming convention. The owner is already
  editing the template to add `onExit:`, so naming the suite on the same line
  costs nothing, keeps "which rubric graded this output" readable from the
  template, and needs no lookup logic.
- **Report-only in this phase**: a low pass rate does **not** affect the
  workflow run's status. The eval observes and logs; it does not decide, block,
  or retrigger. The eval handler succeeds as long as it ran and produced a
  report. (Gating/human-in-the-loop is story 05, and is deferred.)

## Out of scope

- What the eval does internally (reading the output, judging) — story 03.
- The shape of the report it emits — story 04.
- What happens when the pass rate is below threshold — story 05. This story
  only guarantees the eval *runs* on success and reports.
- Fully zero-touch triggering with no edit to the workflow (Argo Events /
  external watcher) — deferred; Milestone 1 accepts the one-line `onExit:`.

## Open questions

_None._ (Story-01 scope is resolved: one suite per workflow, so the `onExit`
handler references exactly one suite for the workflow it is attached to.)
