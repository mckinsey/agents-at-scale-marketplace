# Evolving the framework — what the literature says, mapped to our design

Milestone 1 evaluates a **single produced JSON file** with three check types
(`structural` = L1 deterministic existence/literal, `exact` = L2 deterministic
value equality, `judge` = L3 LLM-as-judge with per-dimension 1–5 rubric scoring
+ per-dimension thresholds). This note records what current research and
state-of-the-art frameworks say about making an agent-eval framework more
capable, and maps each idea onto a concrete, incremental change to *our*
model — so future work is grounded, not guessed.

Sources are recent primary papers and official framework docs, adversarially
fact-checked. Citations are inline.

---

## Where our current design already aligns with SOTA

Worth stating first, because it frames everything else:

- **Deterministic checks belong at the base.** promptfoo splits assertions into
  a *deterministic* tier (programmatic: equality, contains, regex, is-json) and
  a *model-assisted* tier (LLM/ML graders). Our `structural`/`exact` map onto
  the deterministic tier and `judge` onto the model-assisted tier — this
  two-tier taxonomy is the recommended extensibility backbone.
  [promptfoo docs](https://www.promptfoo.dev/docs/configuration/expected-outputs/)
- **Rubric-based, per-dimension judging is the right shape** for free text, and
  reference-free rubric judging is explicitly recommended for when no gold
  answer exists — which is our `judge` case.
  [Google ADK](https://adk.dev/evaluate/)
- **The engine recomputing pass/fail from dimension scores** (not trusting the
  judge's own verdict) is sound: LLM judges are not inherently trustworthy and
  their outputs need validation.
  [Shankar et al.](https://arxiv.org/abs/2404.12272)

So Milestone 1 is a defensible base. The gaps below are about *breadth of case
types* and *statistical honesty*, not a wrong foundation.

---

## The five evolution axes, each mapped to our model

### 1. Judge reliability — from one judge to a calibrated panel

**What the literature says.** A strong single judge (GPT-4) reaches ~85%
agreement with humans — but only ties-excluded; with ties counted it drops to
~66%, so agreement must be *measured*, not assumed
([Zheng et al., MT-Bench](https://arxiv.org/abs/2306.05685)). Single judges
carry documented biases — position, verbosity/length, self-enhancement
(self-preference), concreteness
([Survey on LLM-as-a-Judge](https://arxiv.org/abs/2411.15594)). A **Panel of
LLM evaluators (PoLL)** — several *smaller* models from *disjoint families*,
voting — beats a single large judge, has less intra-model bias, and is ~7×
cheaper ([Verga et al., "Replacing Judges with Juries"](https://arxiv.org/abs/2404.18796)).
Position bias is mitigated by **swapping order and averaging**
([Survey](https://arxiv.org/abs/2411.15594); [PandaLM](https://arxiv.org/abs/2306.05087)).
Caveat: multi-run aggregation is *not* universally beneficial — majority voting
helps, but naive mean / best-of-N can hurt, and panel quality depends heavily
on model choice ([Survey §5.2.2](https://arxiv.org/abs/2411.15594)).

**Maps to our model.** Today `suite.json` has one `judge_model`. Evolution:
- Let `judge_model` be a **list** of Ark `Model`s (a panel). Aggregate by
  **majority vote** for the pass/fail decision (not mean of scores).
- Since judging is via an Ark `Query`, a panel is N Queries → all traced.
- Add a **calibration mode**: a small set of human-labelled cases the suite is
  checked against, reporting judge↔human agreement so the author *knows* the
  judge is trustworthy for their task before relying on it.

### 2. Beyond the final file — evaluate the trajectory

**What the literature says.** Final-output-only scoring is insufficient for
agents: it "cannot assess intermediate decisions, execution efficiency, or
failure causes," and binary outcome metrics hide the agent's actual progress
([Survey on Evaluation of LLM-based Agents](https://arxiv.org/abs/2503.16416)).
The state of the art evaluates the **trajectory** — the ordered tool calls —
separately from the final response, in two modes:
- **reference-based**: compare observed actions to a gold action sequence, with
  match modes *exact / ordered / unordered / subset*
  ([ADK](https://adk.dev/evaluate/) `tool_trajectory_avg_score`;
  [DeepEval Tool Correctness](https://deepeval.com/docs/metrics-tool-correctness)
  = correctly-used / total tools);
- **reference-free**: an LLM rubric judge scores trajectory coherence/efficiency
  when no gold path exists — necessary because *multiple valid paths usually
  exist* ([Survey 2503.16416](https://arxiv.org/abs/2503.16416)).

**Maps to our model.** This is our single biggest gap: we only read one output
file. Evolution:
- Feed the engine the **trajectory** too (an ordered list of tool calls) — in
  Ark terms, from the `Query`/workflow-node record, not just the produced file.
- Add trajectory check types alongside the JSON checks: a **`tool_sequence`**
  reference-based check with a `match` mode (`exact`/`ordered`/`unordered`/
  `subset`), and reuse `judge` for reference-free trajectory scoring.
- Note this composes with our existing `slice` idea — a slice would just point
  into the trajectory record instead of the output document.

### 3. State/outcome checks — generalize `exact` to a goal state

**What the literature says.** τ-bench evaluates success by comparing the final
data-store **state** against an annotated **goal state** (plus checking required
outputs were communicated) — outcome-based, not process-based
([τ-bench](https://arxiv.org/abs/2406.12045)).

**Maps to our model.** Our `exact` check is already outcome/state matching, but
only literal field equality. Evolution: generalize it to assert against a
**goal-state spec** (a set of expected key/value conditions, subset match), so a
case can say "the final state contains these facts" rather than "this exact
field equals this exact literal."

### 4. Non-determinism — multi-run, pass@k / pass^k, error bars

**What the literature says.** Single-run scores overstate reliability. Two
metrics from opposite ends:
- **pass@k** (lenient): probability at least one of k samples passes — capability
  ([Codex/HumanEval](https://arxiv.org/abs/2107.03374): 28.8% single-sample →
  70.2% with 100 samples);
- **pass^k** (strict): fraction of tasks where *all* k runs succeed — reliability
  ([τ-bench](https://arxiv.org/abs/2406.12045): SOTA agents drop below 25% at
  pass^8).

Scores should carry **error bars** via the CLT (`mean ± 1.96·SE`), with
*clustered* SEs when cases come in related groups (naive SEs can understate by
~3×), variance reduced by resampling K times (`σ²/K`) — **not** by lowering
temperature — and system-vs-system comparisons done on **paired differences**
([Miller, "Adding Error Bars to Evals," Anthropic](https://arxiv.org/abs/2411.00640)).

**Maps to our model.** Today each case runs once; the report is a point
estimate. Evolution:
- Add a suite-level **`runs: N`** — evaluate each case N times.
- Report **pass@k** (capability) and **pass^k** (reliability) per case, and a
  confidence interval on the aggregate pass rate.
- This is a natural extension of the report (story 04), not a new mechanism —
  the onExit trigger and engine stay the same, we just loop and aggregate.

### 5. The dataset should grow from production — traces → cases

**What the literature says.** The dataset is not written once. The practitioner
workflow is **error analysis on production traces**: read traces, write
open-ended notes on undesired behavior, cluster into a **failure taxonomy**, and
promote recurring failures into new test cases
([Hamel Husain, "Field Guide"](https://hamel.dev/blog/posts/field-guide/)).
Judges must be **aligned to a domain expert** by iterating the judge prompt to
high agreement (they hit >90% in three iterations), and *raw agreement is a
misleading calibration metric* — use it carefully
([Shankar et al.](https://arxiv.org/abs/2404.12272)).

**Maps to our model.** Milestone 1 has a hand-written golden dataset and no
history. Evolution (this is the "Ruolo B/feedback-loop" territory from the HTML
overview): capture failing production runs as candidate cases, group them by a
failure taxonomy, and let a human promote them into `dataset.json`. This is
where Langfuse becomes more than passive tracing — its stored traces are the
raw material for new cases.

---

## A concrete, ordered roadmap for our engine

Ordered by value-per-effort, each item is additive (no rewrite of Milestone 1):

| # | Change | Axis | Effort | Why now / why later |
|---|--------|------|--------|---------------------|
| 1 | `runs: N` + pass@k / pass^k + CI in the report | 4 | low | Highest honesty-per-line: turns a point estimate into a reliability signal; pure engine+report change. |
| 2 | Position-swap + a judge **panel** (`judge_model` as a list, majority vote) | 1 | medium | Directly attacks judge bias; each judge is just another Ark Query. |
| 3 | Generalize `exact` → **goal-state** subset match | 3 | low | Small grammar addition; makes outcome checks expressive. |
| 4 | **Trajectory** input + `tool_sequence` check (match modes) | 2 | high | The biggest capability gain, but needs the engine to ingest the tool-call record, not just the file. |
| 5 | Judge **calibration** against human labels (report agreement) | 1 | medium | Makes the judge trustworthy for a given task; pairs with the panel. |
| 6 | Traces → cases growth loop + failure taxonomy | 5 | high | The feedback-loop milestone; depends on 1–5 being solid first. |

**Guiding principle from the literature, and from our own design:** keep the
cheap deterministic checks at the base (they never flake and cost nothing), add
model-assisted breadth above them, and be statistically honest about
non-determinism. Every item above slots into the existing two-tier taxonomy
(deterministic vs model-assisted) rather than replacing it.

---

## Caveats worth carrying forward

- The "80%+ human agreement" headline for LLM judges is **ties-excluded**; real
  agreement is ~66%. Calibrate your own judge; don't trust the headline.
  ([Zheng et al.](https://arxiv.org/abs/2306.05685))
- Multi-run aggregation is **not** always beneficial — majority voting helps,
  naive mean/best-of-N can hurt; panel composition matters a lot.
  ([Survey §5.2.2](https://arxiv.org/abs/2411.15594))
- pass@k and pass^k are **opposite** in strictness (any-of-k vs all-k). Report
  both; never conflate them. ([τ-bench](https://arxiv.org/abs/2406.12045))
- Some practitioners argue **binary** judge decisions beat Likert scales (graders
  can't reliably distinguish adjacent levels; capture nuance in a free-text
  critique instead). Our 1–5 per-dimension scoring is the common choice, but a
  binary+critique mode is a legitimate alternative to evaluate.
  ([Shankar et al.](https://arxiv.org/abs/2404.12272))

## Primary sources

- Zheng et al., *Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena* — https://arxiv.org/abs/2306.05685
- *A Survey on LLM-as-a-Judge* — https://arxiv.org/abs/2411.15594
- Verga et al., *Replacing Judges with Juries (PoLL)* — https://arxiv.org/abs/2404.18796
- *A Survey on Evaluation of LLM-based Agents* — https://arxiv.org/abs/2503.16416
- Yao et al., *τ-bench* — https://arxiv.org/abs/2406.12045
- Chen et al., *Evaluating LLMs Trained on Code (Codex, pass@k)* — https://arxiv.org/abs/2107.03374
- Miller, *Adding Error Bars to Evals* (Anthropic) — https://arxiv.org/abs/2411.00640
- Shankar et al., *Who Validates the Validators?* — https://arxiv.org/abs/2404.12272
- Google ADK evaluation docs — https://adk.dev/evaluate/
- promptfoo assertions & metrics — https://www.promptfoo.dev/docs/configuration/expected-outputs/
- Hamel Husain, *A Field Guide to Rapidly Improving AI Products* — https://hamel.dev/blog/posts/field-guide/
