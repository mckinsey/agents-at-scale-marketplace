"""Data models for a suite, its cases, and per-case results.

A suite (story 01) grades one workflow's output. Each case (story 03) targets a
**slice** of that output and declares a **check type**:

- ``structural`` (L1): the slice exists / equals a literal — deterministic.
- ``exact`` (L2): the slice equals the expected value — deterministic.
- ``judge`` (L3): an LLM judge scores the slice against a rubric.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class CheckType(str, Enum):
    """How a case verifies its slice — the pyramid level (story 03)."""

    STRUCTURAL = "structural"  # L1 — deterministic shape/contract
    EXACT = "exact"  # L2 — deterministic value equality
    REGEX = "regex"  # L2 — deterministic pattern match (substring, format, ...)
    SCHEMA = "schema"  # L2 — deterministic JSON Schema validation (Draft 2020-12)
    JUDGE = "judge"  # L3 — LLM-as-judge on free text


class EvalCase(BaseModel):
    """One golden case: a slice of the output + how to check it.

    Extra keys are allowed so a suite author can attach notes without a schema
    change.
    """

    model_config = ConfigDict(extra="allow")

    id: str
    description: str = ""
    #: JSONPath-like pointer into the produced output. ``$`` (or omitted) means
    #: the whole document. See :mod:`ark_evals.slicing` for the supported subset.
    slice: str = "$"
    check: CheckType
    #: For ``structural``/``exact``: the expected value/shape. For ``judge``:
    #: unused by scoring, passed to the judge as context.
    expected: Any = None
    #: For ``judge`` cases: which judge to run (a key under the suite's judges),
    #: default ``quality``.
    judge: str = "quality"
    #: For ``judge`` cases: documents the judge may treat as the evidence the
    #: workflow had (grounding), so faithfulness is scored fairly.
    source_documents: list[dict[str, Any]] = Field(default_factory=list)


class JudgeSpec(BaseModel):
    """A judge's prompt + the JSON schema its verdict must match (story 01)."""

    prompt: str
    schema_: dict[str, Any] = Field(alias="schema")
    #: Per-dimension minimum scores; a dimension below its threshold fails the
    #: case. Dimensions absent here use ``default_dimension_threshold``.
    thresholds: dict[str, int] = Field(default_factory=dict)

    model_config = ConfigDict(populate_by_name=True)


class Suite(BaseModel):
    """A complete eval suite loaded from a mounted ConfigMap (story 01)."""

    name: str
    #: Ark ``Model`` name used as the judge (reused, not defined here).
    judge_model: str
    #: Minimum acceptable pass rate; the report's verdict compares to this.
    threshold: float = 0.80
    #: Cutoff for any judge dimension without an explicit threshold.
    default_dimension_threshold: int = 3
    cases: list[EvalCase] = Field(default_factory=list)
    judges: dict[str, JudgeSpec] = Field(default_factory=dict)


class JudgeVerdict(BaseModel):
    """Structured judge output after schema validation (story 03)."""

    overall_pass: bool
    dimension_scores: dict[str, int] = Field(default_factory=dict)
    auto_fail_triggered: list[str] = Field(default_factory=list)
    rationale: dict[str, str] = Field(default_factory=dict)
    improvement_suggestions: list[str] = Field(default_factory=list)


class CaseResult(BaseModel):
    """The outcome of grading one case.

    ``error`` set means the case could not be evaluated (missing slice, judge
    schema mismatch) — distinct from ``passed=False`` which means it was graded
    and scored below bar (story 04/05).
    """

    case_id: str
    check: CheckType
    slice: str
    passed: bool = False
    #: Human-readable reason a case failed (expected vs actual, dimension miss).
    detail: str = ""
    #: Set when the case could not be evaluated at all.
    error: str | None = None
    #: Present for judge cases.
    verdict: JudgeVerdict | None = None


class RunReport(BaseModel):
    """Aggregate of all case results for one suite run (story 04)."""

    suite: str
    judge_model: str
    output_path: str
    workflow: str = ""
    threshold: float = 0.80
    total: int = 0
    passed: int = 0
    failed: int = 0
    errored: int = 0
    results: list[CaseResult] = Field(default_factory=list)

    @property
    def pass_rate(self) -> float:
        """Passed / evaluated. Errored cases are excluded from the denominator."""
        evaluated = self.passed + self.failed
        return (self.passed / evaluated) if evaluated else 0.0

    @property
    def below_threshold(self) -> bool:
        return self.pass_rate < self.threshold
