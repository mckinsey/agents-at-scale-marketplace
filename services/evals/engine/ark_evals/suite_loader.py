"""Load and validate a suite from a mounted ConfigMap directory (story 01).

The suite folder is materialized into a ConfigMap where each file becomes one
key. Because ConfigMap keys cannot contain ``/``, the ``judges/`` files are
flattened to dotted keys when the ConfigMap is built:

    suite.json
    dataset.json
    judges.quality.prompt.txt
    judges.quality.schema.json

When a ConfigMap is mounted as a volume, each key is a file in the mount dir.
This loader reads that directory. ``suite.json`` is the entry point.

Validation is strict and the errors are didactic (story 06): a malformed suite
is a clear configuration error, never a silent partial run.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from .schemas import CheckType, EvalCase, JudgeSpec, Suite


class SuiteError(ValueError):
    """The suite on disk is malformed or incomplete (story 01 acceptance)."""


def _read_json(path: Path, what: str) -> Any:
    if not path.exists():
        raise SuiteError(f"{what} not found at {path.name}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SuiteError(f"{what} ({path.name}) is not valid JSON: {exc}") from exc


def load_suite(mount_dir: str | Path) -> Suite:
    """Load, assemble, and validate a suite from a mounted ConfigMap directory."""
    root = Path(mount_dir)
    if not root.is_dir():
        raise SuiteError(f"suite mount directory not found: {root}")

    meta = _read_json(root / "suite.json", "suite.json")
    if not isinstance(meta, dict):
        raise SuiteError("suite.json must be a JSON object")

    name = meta.get("name")
    judge_model = meta.get("judge_model")
    if not name:
        raise SuiteError("suite.json is missing required field 'name'")
    if not judge_model:
        raise SuiteError("suite.json is missing required field 'judge_model' (the Ark Model)")

    dataset = _read_json(root / "dataset.json", "dataset.json")
    if not isinstance(dataset, list):
        raise SuiteError("dataset.json must be a JSON array of case objects")

    cases: list[EvalCase] = []
    for i, raw in enumerate(dataset):
        try:
            cases.append(EvalCase.model_validate(raw))
        except ValidationError as exc:
            cid = raw.get("id", f"index {i}") if isinstance(raw, dict) else f"index {i}"
            raise SuiteError(f"case {cid} is invalid: {_first_error(exc)}") from exc
    if not cases:
        raise SuiteError("dataset.json has no cases")

    judges = _load_judges(root, meta)

    # Every judge case must reference a judge that exists (story 06 didactic).
    for case in cases:
        if case.check is CheckType.JUDGE and case.judge not in judges:
            raise SuiteError(
                f"case {case.id!r} is a 'judge' case referencing judge "
                f"{case.judge!r}, but the suite defines no such judge "
                f"(available: {sorted(judges) or 'none'})"
            )

    try:
        return Suite(
            name=name,
            judge_model=judge_model,
            threshold=float(meta.get("threshold", 0.80)),
            default_dimension_threshold=int(meta.get("default_dimension_threshold", 3)),
            cases=cases,
            judges=judges,
        )
    except (ValidationError, ValueError) as exc:
        raise SuiteError(f"suite.json is invalid: {exc}") from exc


def _load_judges(root: Path, meta: dict[str, Any]) -> dict[str, JudgeSpec]:
    """Assemble judges from ``judges.<name>.prompt.txt`` + ``.schema.json``."""
    judges: dict[str, JudgeSpec] = {}
    prompt_files = sorted(root.glob("judges.*.prompt.txt"))
    thresholds_cfg = meta.get("judge_thresholds", {}) or {}

    for prompt_path in prompt_files:
        # judges.quality.prompt.txt -> "quality"
        judge_name = prompt_path.name[len("judges.") : -len(".prompt.txt")]
        schema_path = root / f"judges.{judge_name}.schema.json"
        if not schema_path.exists():
            raise SuiteError(
                f"judge {judge_name!r} has a prompt ({prompt_path.name}) but no "
                f"schema ({schema_path.name}); every judge prompt needs its schema"
            )
        schema = _read_json(schema_path, f"judge {judge_name} schema")
        if not isinstance(schema, dict):
            raise SuiteError(f"judge {judge_name!r} schema must be a JSON object")
        judges[judge_name] = JudgeSpec(
            prompt=prompt_path.read_text(encoding="utf-8"),
            schema=schema,
            thresholds=thresholds_cfg.get(judge_name, {}),
        )
    return judges


def _first_error(exc: ValidationError) -> str:
    errs = exc.errors()
    if not errs:
        return str(exc)
    e = errs[0]
    loc = ".".join(str(p) for p in e.get("loc", []))
    return f"{loc}: {e.get('msg', '')}"
