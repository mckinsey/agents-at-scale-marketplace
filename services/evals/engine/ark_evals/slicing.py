"""Resolve a case's ``slice`` against the produced output document.

A deliberately small, predictable JSONPath subset — enough to point at a field
in a KYC-style structured document, without pulling a full JSONPath dependency.
Supported syntax:

- ``$``                          the whole document
- ``$.key``                      object key
- ``$.a.b.c``                    nested keys
- ``$.list[0]``                  list index
- ``$.a[0].b``                   mix of keys and indices

A slice that does not resolve raises :class:`SliceError` with a message that
names the path and where it broke (story 06: didactic errors).
"""

from __future__ import annotations

import re
from typing import Any

_TOKEN = re.compile(r"\.([^.\[\]]+)|\[(\d+)\]")


class SliceError(ValueError):
    """A slice expression did not resolve against the document."""


def resolve_slice(document: Any, expr: str) -> Any:
    """Return the value at ``expr`` within ``document`` or raise ``SliceError``."""
    expr = (expr or "$").strip()
    if expr in ("$", ""):
        return document

    if not expr.startswith("$"):
        raise SliceError(
            f"slice {expr!r} must start with '$' (e.g. '$.\"Inquiry information\"[0]')"
        )

    rest = expr[1:]
    pos = 0
    current: Any = document
    walked = "$"

    for match in _TOKEN.finditer(rest):
        if match.start() != pos:
            bad = rest[pos : match.start()]
            raise SliceError(f"slice {expr!r}: cannot parse segment {bad!r} after {walked}")
        pos = match.end()
        key, index = match.group(1), match.group(2)

        if key is not None:
            key = key.strip().strip('"').strip("'")
            if not isinstance(current, dict):
                raise SliceError(
                    f"slice {expr!r}: expected an object at {walked} to read key "
                    f"{key!r}, found {type(current).__name__}"
                )
            if key not in current:
                raise SliceError(
                    f"slice {expr!r}: key {key!r} not found at {walked} "
                    f"(available: {sorted(current)[:8]})"
                )
            current = current[key]
            walked += f".{key}"
        else:
            idx = int(index)
            if not isinstance(current, list):
                raise SliceError(
                    f"slice {expr!r}: expected a list at {walked} to read index "
                    f"[{idx}], found {type(current).__name__}"
                )
            if idx >= len(current):
                raise SliceError(
                    f"slice {expr!r}: index [{idx}] out of range at {walked} "
                    f"(length {len(current)})"
                )
            current = current[idx]
            walked += f"[{idx}]"

    if pos != len(rest):
        raise SliceError(f"slice {expr!r}: trailing characters {rest[pos:]!r}")

    return current
