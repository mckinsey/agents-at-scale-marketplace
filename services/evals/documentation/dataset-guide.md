# Authoring `dataset.json` — a step-by-step guide

This guide explains how to write the `dataset.json` of an eval suite: the list
of golden cases the engine grades a workflow's output against. It is written to
be usable **both by a human author and by an AI agent** generating a suite from
scratch — every field, its type, its default, and every allowed value is stated
explicitly, with no reliance on reading the engine source.

> Where this fits: a suite is a folder (`suite.json` + `dataset.json` +
> `judges/`). This guide covers `dataset.json` only. For the suite as a whole
> see [`01-configure-eval-suite.md`](01-configure-eval-suite.md); for how a case
> is graded see [`03-evaluate-produced-output.md`](03-evaluate-produced-output.md).

---

## 1. What `dataset.json` is

A single JSON **array** of **case objects**. Each case checks one thing about
the workflow's produced output (a JSON document): it points at a **slice** of
that output and declares **how** to verify it.

```json
[
  { "id": "...", "check": "...", "slice": "...", ... },
  { "id": "...", "check": "...", "slice": "...", ... }
]
```

The array must be non-empty. The engine rejects a suite whose `dataset.json` is
not a JSON array, is empty, or contains a malformed case — with a clear error,
never a silent skip.

---

## 2. The case object — every field

| Field | Type | Required | Default | Applies to | Meaning |
|-------|------|----------|---------|-----------|---------|
| `id` | string | **yes** | — | all | Unique identifier for the case; appears in the report. |
| `check` | enum | **yes** | — | all | How to verify the slice. One of `structural`, `exact`, `judge` (see §3). |
| `slice` | string | no | `"$"` | all | JSONPath-subset pointer into the output (see §4). `"$"` = whole document. |
| `expected` | any | conditional | `null` | `structural`, `exact` | The value the slice must equal (see §3). Ignored by `judge`. |
| `judge` | string | no | `"quality"` | `judge` | Which judge to use — a key under the suite's `judges/`. |
| `source_documents` | array of objects | no | `[]` | `judge` | Evidence the judge scores against (grounding). Each object is free-form, e.g. `{"title": "...", "content": "..."}`. |
| `description` | string | no | `""` | all | Human note; not used by scoring. |

Extra keys are allowed and ignored by scoring, so you may annotate a case
freely (e.g. `"rationale_for_case": "..."`).

---

## 3. `check` — the one enum, and what each value needs

`check` is the only enumerated field. **Allowed values (exactly these three):**

### `structural` — L1, deterministic, no model call
Verifies shape/contract. Two modes, decided by whether `expected` is present:

- **`expected` omitted** → passes if the slice **exists** (resolves at all).
  Use it to assert a field/section is present.
- **`expected` present** → passes if the slice **equals** that literal value.
  Use it for fixed literals like a status flag.

```json
{ "id": "sections-present", "check": "structural", "slice": "$.\"Inquiry information\"" }
{ "id": "status-pending", "check": "structural",
  "slice": "$.\"Inquiry information\"[0].content[0].\"validation status\"",
  "expected": "_Pending_" }
```

### `exact` — L2, deterministic, no model call
Passes if the slice **equals** `expected`. `expected` is **required** here.
Comparison is exact (types matter: `"5"` ≠ `5`; arrays/objects compared by deep
equality).

```json
{ "id": "company-name", "check": "exact",
  "slice": "$.\"Inquiry information\"[0].content[0].\"Company Name\"",
  "expected": "Associated British Foods (ABF)" }
```

### `judge` — L3, calls the LLM judge
Sends the slice to the judge model (an Ark `Model`, via an Ark Query) and scores
it against the judge's rubric. `expected` is **not** used for scoring (you may
still include it as context). Provide `source_documents` so faithfulness /
groundedness is judged against the evidence the workflow actually had.

```json
{ "id": "purpose-faithful", "check": "judge", "judge": "quality",
  "slice": "$.\"Inquiry information\"[2].content[2].\"Account purpose\"",
  "source_documents": [
    { "title": "Inquiry email", "content": "We would like to open a Corporate Treasury Management Account..." }
  ] }
```

**Choosing the check — the rule:** pick the *cheapest check that can see the
failure*. Reach for `structural`/`exact` whenever the correct answer is known
and fixed (they never flake and cost nothing); use `judge` only for free text
whose quality is a matter of degree.

| If you want to verify... | Use |
|--------------------------|-----|
| a field/section exists | `structural` (no `expected`) |
| a field equals a fixed literal (a flag, an enum value) | `structural` (with `expected`) |
| an extracted value equals a known-correct value | `exact` |
| free text is faithful / complete / well-toned | `judge` |

---

## 4. `slice` — the JSONPath subset

A slice points into the produced JSON document. The supported syntax is a small,
predictable subset (not full JSONPath):

| Syntax | Meaning |
|--------|---------|
| `$` (or omit `slice`) | the whole document |
| `$.key` | object key |
| `$.a.b.c` | nested keys |
| `$.list[0]` | list index (0-based) |
| `$.a[0].b` | keys and indices mixed |
| `$."key with spaces"` | quoted key (needed when a key contains spaces or dots) — in JSON you write `$.\"key with spaces\"` |

**Not supported** (will fail to parse or resolve): wildcards (`*`), recursive
descent (`..`), filters (`[?(...)]`), slices (`[0:2]`), functions. If you need
these, see §7 — they are candidates for a future version.

A slice that does not resolve produces a **case error** (not a fail) whose
message names the path, where it broke, and the keys actually available — e.g.:

```
slice '$.NoSuchKey': key 'NoSuchKey' not found at $ (available: ['Inquiry information'])
```

---

## 5. Pass / fail / error — how a case is scored

- **pass** — the check succeeded.
- **fail** — the check ran and the output was wrong (`exact` mismatch, a judge
  dimension below its threshold, or an `auto_fail_triggered`).
- **error** — the case could **not** be evaluated (slice did not resolve, judge
  returned an unparseable/invalid verdict). An error is *not* a fail: it means
  "could not judge", and it is excluded from the pass-rate denominator.

For `judge` cases, pass/fail is **recomputed by the engine** from the
per-dimension scores against the suite thresholds — the judge's own
`overall_pass` is not trusted on its own. Two dimension names are **scored but
never fail a case on their own** (informational): `claim_support` and
`source_traceability`.

Thresholds live in `suite.json`, not in the dataset:
`threshold` (run pass-rate bar), `default_dimension_threshold` (default per
judge dimension, 3), and `judge_thresholds.<judge>.<dimension>` (overrides).

---

## 6. End-to-end example

A minimal but complete suite that grades a KYC-style extraction output.

**The output under evaluation** (what the workflow produced):

```json
{
  "Inquiry information": [
    { "subsection": "Company details",
      "content": [
        { "Company Name": "Associated British Foods (ABF)", "validation status": "_Pending_" }
      ] },
    { "subsection": "Inquiry details",
      "content": [
        { "Account purpose": "To open a Corporate Treasury Management Account to optimize global cash flow." }
      ] }
  ]
}
```

**`dataset.json`** (three cases, one per check type):

```json
[
  {
    "id": "sections-present",
    "check": "structural",
    "slice": "$.\"Inquiry information\"",
    "description": "the top-level section exists"
  },
  {
    "id": "company-name-extracted",
    "check": "exact",
    "slice": "$.\"Inquiry information\"[0].content[0].\"Company Name\"",
    "expected": "Associated British Foods (ABF)"
  },
  {
    "id": "purpose-faithful",
    "check": "judge",
    "judge": "quality",
    "slice": "$.\"Inquiry information\"[1].content[0].\"Account purpose\"",
    "source_documents": [
      { "title": "Inquiry email", "content": "We would like to open a Corporate Treasury Management Account to optimize our global cash flow." }
    ]
  }
]
```

**`suite.json`** that ties it together:

```json
{
  "name": "kyc-profile-init",
  "judge_model": "default",
  "threshold": 0.80,
  "default_dimension_threshold": 3,
  "judge_thresholds": { "quality": { "relevance": 3, "groundedness": 3, "tone_clarity": 3 } }
}
```

**`judges/quality.prompt.txt`** must instruct the judge to return the keys the
schema requires (`overall_pass`, `dimension_scores`, `auto_fail_triggered`,
`rationale`, `improvement_suggestions`), and **`judges/quality.schema.json`**
must declare those as `required` with `dimension_scores` holding
`relevance` / `groundedness` / `tone_clarity` as integers 1–5. (See the
reference suite under `chart/files/kyc-profile-init/`.)

**Validate before running** (no model calls, no cluster needed):

```bash
python -m ark_evals validate --suite-dir <suite-dir>
```

Expected result on the output above: `sections-present` pass, `company-name`
pass, `purpose-faithful` pass → **100%**. If the extractor instead wrote
`"Associated British Foods plc"`, `company-name` fails with
`expected "Associated British Foods (ABF)", got "Associated British Foods plc"`
→ **67%**, below the 80% threshold → `BELOW-THRESHOLD` in the report.

---

## 7. Checklist for an author (human or agent)

1. Every case has a unique `id` and a valid `check` (`structural` / `exact` / `judge`).
2. `exact` cases have `expected`. `structural` cases have `expected` only if
   asserting a literal.
3. Every `judge` case's `judge` names a judge that exists under `judges/`.
4. Every `slice` uses only the supported subset (§4) and resolves against a
   representative output document.
5. Prefer `structural`/`exact` over `judge` wherever the answer is fixed.
6. Run `python -m ark_evals validate --suite-dir <dir>` and fix every reported
   error before wiring the suite to a workflow.
