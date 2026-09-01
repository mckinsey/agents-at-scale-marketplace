# Authoring `dataset.json` — a step-by-step guide

This guide explains how to write the `dataset.json` of an eval suite: the list
of golden cases the engine grades a workflow's output against. It is written to
be usable **both by a human author and by an AI agent** generating a suite from
scratch — every field, its type, its default, and every allowed value is stated
explicitly, with no reliance on reading the engine source.

> Where this fits: a suite is a folder (`suite.json` + `dataset.json` +
> `judges/`). This guide covers `dataset.json` only. For the suite as a whole
> see [`user-stories/01-configure-eval-suite.md`](user-stories/01-configure-eval-suite.md);
> for how a case is graded see
> [`user-stories/03-evaluate-produced-output.md`](user-stories/03-evaluate-produced-output.md).

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
| `check` | enum | **yes** | — | all | How to verify the slice. One of `structural`, `exact`, `regex`, `schema`, `judge` (see §3). |
| `source` | enum | no | `"output"` | all | Which document the slice resolves against: `output` (what the workflow produced) or `input` (what it was given, e.g. the source email). `input` needs the run to be given the input location — see §5. |
| `slice` | string | no | `"$"` | all | JSONPath-subset pointer into the chosen document (see §4). `"$"` = whole document. |
| `expected` | any | conditional | `null` | `structural`, `exact`, `regex`, `schema` | The value the slice must equal; for `regex`, the pattern string; for `schema`, a JSON Schema object (see §3). Ignored by `judge`. |
| `judge` | string | no | `"quality"` | `judge` | Which judge to use — a key under the suite's `judges/`. |
| `source_documents` | array of objects | no | `[]` | `judge` | Evidence the judge scores against (grounding). Each object is free-form, e.g. `{"title": "...", "content": "..."}`. |
| `description` | string | no | `""` | all | Human note; not used by scoring. |

Extra keys are allowed and ignored by scoring, so you may annotate a case
freely (e.g. `"rationale_for_case": "..."`).

---

## 3. `check` — the one enum, and what each value needs

`check` is the only enumerated field. **Allowed values (exactly these five):**

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

### `regex` — L2, deterministic, no model call
Passes if the slice, as a string, **matches the regular expression** in
`expected` (Python `re.search`, so an unanchored pattern acts as "contains").
`expected` is **required** and must be a pattern string. Non-string slices are
coerced to their JSON string form before matching, so numbers/lists can still
be pattern-matched. An **invalid** pattern is a case **error** (a broken test),
not a fail.

Use it for substring checks, case-insensitive checks, and format/shape checks:

```json
{ "id": "purpose-mentions-treasury", "check": "regex",
  "slice": "$.\"Inquiry information\"[2].content[2].\"Account purpose\"",
  "expected": "Treasury" }
{ "id": "purpose-mentions-treasury-ci", "check": "regex",
  "slice": "$.\"Inquiry information\"[2].content[2].\"Account purpose\"",
  "expected": "(?i)treasury" }
{ "id": "company-number-is-8-digits", "check": "regex",
  "slice": "$.\"Inquiry information\"[0].content[2].\"Company Number\"",
  "expected": "^\\d{8}$" }
```

Common patterns: `"Treasury"` (contains), `"(?i)treasury"` (case-insensitive),
`"^\\d{8}$"` (exactly 8 digits), `"\\d{4}-\\d{2}-\\d{2}"` (an ISO-ish date),
`"@"` (looks like an email). Remember JSON needs the backslash doubled
(`\\d`, not `\d`).

### `schema` — L2, deterministic, no model call
Passes if the slice **validates against the JSON Schema** (Draft 2020-12) in
`expected`. This is the *powerful* deterministic check: one type covers `type`,
`enum`, `pattern`, `required`, `minLength`/`maxLength`, `minimum`/`maximum`,
`minItems`, nested object/array shapes, and more — using the JSON Schema
standard rather than a bespoke grammar. A malformed schema is a case **error**;
a value that fails validation is a **fail** with the specific violation.

```json
{ "id": "purpose-is-nonempty-string", "check": "schema",
  "slice": "$.\"Inquiry information\"[2].content[2].\"Account purpose\"",
  "expected": { "type": "string", "minLength": 10 } }
{ "id": "company-number-8-digits", "check": "schema",
  "slice": "$.\"Inquiry information\"[0].content[2].\"Company Number\"",
  "expected": { "type": "string", "pattern": "^\\d{8}$" } }
{ "id": "status-is-known-value", "check": "schema",
  "slice": "$.\"Inquiry information\"[0].content[0].\"validation status\"",
  "expected": { "enum": ["_Pending_", "_Validated_"] } }
{ "id": "at-least-one-product", "check": "schema",
  "slice": "$.\"Inquiry information\"[2].content[1].\"Product requested\"",
  "expected": { "type": "array", "minItems": 1 } }
```

**`structural` / `exact` / `regex` vs `schema`.** The first three are
*ergonomic shortcuts* for the common cases — `exact` with `expected: "ACME"`
reads better than `schema` with `{"const": "ACME"}`, and `regex` with
`"Treasury"` beats `{"type": "string", "pattern": "Treasury"}`. Reach for
`schema` when you need type/enum/range/array/nested validation the shortcuts
can't express. Both tiers are deterministic and free.

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
| a value **contains** a substring, or matches a simple **pattern** | `regex` |
| a value has a **type/enum/range/array shape**, or nested structure | `schema` |
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
descent (`..`), filters (`[?(...)]`), slices (`[0:2]`), functions. These are
candidates for a future version; for now, target a fixed index, or use a
`schema` check (whose `items`/`contains` cover "every element" / "at least one"
without wildcards).

A slice that does not resolve produces a **case error** (not a fail) whose
message names the path, where it broke, and the keys actually available — e.g.:

```
slice '$.NoSuchKey': key 'NoSuchKey' not found at $ (available: ['Inquiry information'])
```

---

## 5. `source` — evaluating the input, not just the output

By default a case's `slice` resolves against the workflow's **output**. Set
`source: "input"` to resolve it against the workflow's **input** instead — the
document the workflow was given (e.g. the source email). This is what makes an
*extraction* eval possible: you can assert facts about the input, and — most
importantly — judge whether the output is faithful to it.

`source: "input"` requires the run to be told where the input is (the trigger's
`input-key`, see the service README / chart `NOTES.txt`). If it wasn't, an
`input` case is a clear **error** (not a fail): "targets source 'input' but the
run was given no input-key".

The input is often plain text (an email), not JSON. When it is, `slice: "$"`
gives you the whole text and `regex`/`judge` work on it directly; when the input
is JSON, the normal slice syntax applies.

```json
{ "id": "email-mentions-treasury", "source": "input", "check": "regex",
  "slice": "$", "expected": "(?i)treasury" }
```

**Judge grounding.** Independently of `source`, every `judge` case is given the
real workflow input as a `{workflow_input}` placeholder in its prompt (empty if
no input-key was provided). So a judge prompt can score groundedness against the
actual input rather than a hand-copied excerpt:

```
Score whether the output is faithful to the source the workflow was given.
Output: {output}
Source the workflow was given: {workflow_input}
```

`source_documents` on a case still work as an explicit, per-case evidence list;
`{workflow_input}` is the automatic, always-the-real-thing counterpart.

---

## 6. Pass / fail / error — how a case is scored

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

## 7. End-to-end example

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

## 8. Checklist for an author (human or agent)

1. Every case has a unique `id` and a valid `check` (`structural` / `exact` /
   `regex` / `schema` / `judge`).
2. `exact`, `regex`, and `schema` cases have `expected` (a value / a pattern
   string / a JSON Schema object). `structural` cases have `expected` only if
   asserting a literal.
3. Every `judge` case's `judge` names a judge that exists under `judges/`.
4. Every `slice` uses only the supported subset (§4) and resolves against a
   representative output document.
5. Prefer `structural`/`exact` over `judge` wherever the answer is fixed.
6. Run `python -m ark_evals validate --suite-dir <dir>` and fix every reported
   error before wiring the suite to a workflow.
