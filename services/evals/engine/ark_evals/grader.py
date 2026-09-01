"""Grade each case against the produced output (story 03).

- ``structural`` / ``exact`` : deterministic, no model call.
- ``judge``                   : ask the Ark Model judge, validate the verdict
                                against the judge schema, recompute pass/fail
                                from per-dimension thresholds (the judge's own
                                ``overall_pass`` is not trusted on its own).
"""

from __future__ import annotations

import json
import re
from typing import Any, Callable

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError

from .schemas import (
    CaseResult,
    CheckType,
    EvalCase,
    JudgeSpec,
    JudgeVerdict,
    RunReport,
    Suite,
)
from .slicing import SliceError, resolve_slice

# Dimensions that inform a judge but never fail a case on their own
# (carried over from agentic-evals-service).
_INFORMATIONAL_DIMENSIONS = {"claim_support", "source_traceability"}

#: Signature of the judge callable, so the grader stays testable without a
#: cluster: ``(prompt, model) -> raw judge text``.
JudgeCaller = Callable[[str, str], str]


def grade_suite(
    suite: Suite,
    output: Any,
    *,
    output_path: str,
    workflow: str,
    judge_caller: JudgeCaller,
) -> RunReport:
    """Grade every case in ``suite`` against ``output`` and aggregate a report."""
    report = RunReport(
        suite=suite.name,
        judge_model=suite.judge_model,
        output_path=output_path,
        workflow=workflow,
        threshold=suite.threshold,
    )
    for case in suite.cases:
        report.results.append(_grade_case(case, suite, output, judge_caller))

    report.total = len(report.results)
    report.passed = sum(1 for r in report.results if r.error is None and r.passed)
    report.failed = sum(1 for r in report.results if r.error is None and not r.passed)
    report.errored = sum(1 for r in report.results if r.error is not None)
    return report


def _grade_case(
    case: EvalCase, suite: Suite, output: Any, judge_caller: JudgeCaller
) -> CaseResult:
    result = CaseResult(case_id=case.id, check=case.check, slice=case.slice)
    try:
        actual = resolve_slice(output, case.slice)
    except SliceError as exc:
        result.error = str(exc)
        return result

    if case.check is CheckType.STRUCTURAL:
        return _grade_structural(case, actual, result)
    if case.check is CheckType.EXACT:
        return _grade_exact(case, actual, result)
    if case.check is CheckType.REGEX:
        return _grade_regex(case, actual, result)
    if case.check is CheckType.SCHEMA:
        return _grade_schema(case, actual, result)
    return _grade_judge(case, suite, actual, result, judge_caller)


def _grade_structural(case: EvalCase, actual: Any, result: CaseResult) -> CaseResult:
    """L1: the slice exists, and (if ``expected`` given) equals that literal.

    Reaching here already proves the slice resolved (it exists). When
    ``expected`` is provided, the value must match it exactly.
    """
    if case.expected is None:
        result.passed = True
        result.detail = f"slice {case.slice} exists"
        return result
    if actual == case.expected:
        result.passed = True
        result.detail = f"{case.slice} == {_short(case.expected)}"
    else:
        result.detail = f"expected {_short(case.expected)}, got {_short(actual)}"
    return result


def _grade_exact(case: EvalCase, actual: Any, result: CaseResult) -> CaseResult:
    """L2: the extracted value equals the expected value."""
    if actual == case.expected:
        result.passed = True
        result.detail = f"{case.slice} == {_short(case.expected)}"
    else:
        result.detail = f"expected {_short(case.expected)}, got {_short(actual)}"
    return result


def _grade_regex(case: EvalCase, actual: Any, result: CaseResult) -> CaseResult:
    """L2: the value (as a string) matches the `expected` regular expression.

    Uses ``re.search`` so a plain substring like ``"Treasury"`` works as
    "contains", while full patterns handle case-insensitivity ``(?i)``, dates,
    formats, etc. A slice that is not a string is coerced with ``str()`` so a
    number or list can still be pattern-matched. An invalid pattern is a case
    error (a broken test), not a fail.
    """
    if case.expected is None or not isinstance(case.expected, str):
        result.error = "regex check requires 'expected' to be a pattern string"
        return result
    text = actual if isinstance(actual, str) else json.dumps(actual, ensure_ascii=False)
    try:
        found = re.search(case.expected, text)
    except re.error as exc:
        result.error = f"invalid regex {case.expected!r}: {exc}"
        return result
    if found:
        result.passed = True
        result.detail = f"{case.slice} matches /{case.expected}/"
    else:
        result.detail = f"no match for /{case.expected}/ in {_short(text)}"
    return result


def _grade_schema(case: EvalCase, actual: Any, result: CaseResult) -> CaseResult:
    """L2: the slice validates against the JSON Schema in `expected`.

    Delegates deterministic validation to the `jsonschema` library (Draft
    2020-12), so one check type covers type/enum/pattern/required/min-max/format
    without bespoke code. A malformed schema is a case error (broken test); a
    value that fails validation is a fail with the specific reason.
    """
    if not isinstance(case.expected, dict):
        result.error = "schema check requires 'expected' to be a JSON Schema object"
        return result
    try:
        Draft202012Validator.check_schema(case.expected)
    except SchemaError as exc:
        result.error = f"invalid JSON Schema: {exc.message}"
        return result

    errors = sorted(
        Draft202012Validator(case.expected).iter_errors(actual),
        key=lambda e: list(e.path),
    )
    if not errors:
        result.passed = True
        result.detail = f"{case.slice} validates against schema"
    else:
        first = errors[0]
        loc = "".join(f"[{p!r}]" for p in first.path) or "(root)"
        result.detail = f"schema violation at {loc}: {first.message}"
    return result


def _grade_judge(
    case: EvalCase,
    suite: Suite,
    actual: Any,
    result: CaseResult,
    judge_caller: JudgeCaller,
) -> CaseResult:
    """L3: score the slice with the LLM judge, recompute pass/fail."""
    spec = suite.judges.get(case.judge)
    if spec is None:  # already validated by the loader, defensive here
        result.error = f"judge {case.judge!r} not defined in suite"
        return result

    prompt = _fill_prompt(spec.prompt, case, actual)
    try:
        raw = judge_caller(prompt, suite.judge_model)
    except Exception as exc:  # noqa: BLE001 — surface any judge transport failure
        result.error = f"judge call failed: {type(exc).__name__}: {exc}"
        return result

    try:
        payload = _parse_json(raw)
    except ValueError as exc:
        result.error = f"judge response was not valid JSON: {exc}"
        return result

    ok, reason = _validate_payload(payload, spec.schema_)
    if not ok:
        result.error = f"judge response did not match schema: {reason}"
        return result

    passed = _apply_pass_rules(payload, spec, suite.default_dimension_threshold)
    result.verdict = JudgeVerdict(
        overall_pass=passed,
        dimension_scores=payload.get("dimension_scores", {}),
        auto_fail_triggered=payload.get("auto_fail_triggered", []),
        rationale=payload.get("rationale", {}),
        improvement_suggestions=payload.get("improvement_suggestions", []),
    )
    result.passed = passed
    result.detail = _judge_detail(result.verdict, spec, suite.default_dimension_threshold)
    return result


def _fill_prompt(prompt: str, case: EvalCase, actual: Any) -> str:
    """Fill ``{output}``/``{source_documents}``/``{expected}`` placeholders."""
    try:
        return prompt.format(
            output=json.dumps(actual, ensure_ascii=False),
            source_documents=json.dumps(case.source_documents, ensure_ascii=False),
            expected=json.dumps(case.expected, ensure_ascii=False),
        )
    except (KeyError, ValueError, IndexError):
        # A prompt that uses no placeholders (or an unknown one) is sent as-is,
        # with the graded slice appended so the judge always sees the output.
        return f"{prompt}\n\nOutput under evaluation:\n{json.dumps(actual, ensure_ascii=False)}"


# --- judge payload parsing / validation (adapted from agentic-evals-service) --


def _parse_json(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped)
        stripped = re.sub(r"\s*```$", "", stripped)
    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", stripped, flags=re.DOTALL)
        if not match:
            raise ValueError("no JSON object found in judge response")
        parsed = json.loads(match.group(0))
    if not isinstance(parsed, dict):
        raise ValueError("judge response must be a JSON object")
    return parsed


def _validate_payload(payload: dict[str, Any], schema: dict[str, Any]) -> tuple[bool, str]:
    required = schema.get("required", [])
    missing = [k for k in required if k not in payload]
    if missing:
        return False, f"missing keys {missing}"
    scores = payload.get("dimension_scores", {})
    if not isinstance(scores, dict):
        return False, "dimension_scores must be an object"
    for dim, val in scores.items():
        if not isinstance(val, int) or not (1 <= val <= 5):
            return False, f"dimension_scores.{dim} must be an integer 1-5, got {val!r}"
    return True, "ok"


def _apply_pass_rules(
    payload: dict[str, Any], spec: JudgeSpec, default_threshold: int
) -> bool:
    """Fail on any auto-fail, or any dimension below its threshold."""
    if payload.get("auto_fail_triggered"):
        return False
    for dim, score in payload.get("dimension_scores", {}).items():
        if dim in _INFORMATIONAL_DIMENSIONS:
            continue
        threshold = spec.thresholds.get(dim, default_threshold)
        if score < threshold:
            return False
    return True


def _judge_detail(verdict: JudgeVerdict, spec: JudgeSpec, default_threshold: int) -> str:
    if verdict.auto_fail_triggered:
        return f"auto-fail: {', '.join(verdict.auto_fail_triggered)}"
    misses = [
        f"{dim}={score}<{spec.thresholds.get(dim, default_threshold)}"
        for dim, score in verdict.dimension_scores.items()
        if dim not in _INFORMATIONAL_DIMENSIONS
        and score < spec.thresholds.get(dim, default_threshold)
    ]
    if misses:
        return "below threshold: " + ", ".join(misses)
    scores = ", ".join(f"{d}={s}" for d, s in verdict.dimension_scores.items())
    return f"scores: {scores}"


def _short(value: Any, limit: int = 80) -> str:
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    return text if len(text) <= limit else text[: limit - 1] + "…"
