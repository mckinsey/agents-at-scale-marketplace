"""Read the workflow's produced output from the file-gateway (story 03).

Milestone 1 evaluates a file the workflow already wrote to the shared
file-gateway volume. The engine reads it over the file-gateway REST API
(``GET /files/{key}/download``), so it needs no direct volume mount and no S3
credentials — the same gateway the KYC workflow already uses.
"""

from __future__ import annotations

import json
from typing import Any
from urllib.parse import quote
from urllib.request import urlopen


class OutputError(RuntimeError):
    """The produced output could not be read or parsed (story 03: clear error)."""


def load_output(base_url: str, key: str, *, timeout_sec: int = 30) -> Any:
    """Download ``key`` from the file-gateway and parse it as JSON."""
    url = f"{base_url.rstrip('/')}/files/{quote(key, safe='/')}/download"
    try:
        with urlopen(url, timeout=timeout_sec) as resp:  # noqa: S310 — in-cluster URL
            if resp.status != 200:
                raise OutputError(f"file-gateway returned HTTP {resp.status} for {key}")
            body = resp.read().decode("utf-8")
    except OutputError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise OutputError(
            f"could not read output {key!r} from file-gateway at {base_url}: "
            f"{type(exc).__name__}: {exc}"
        ) from exc

    try:
        return json.loads(body)
    except json.JSONDecodeError as exc:
        raise OutputError(f"output {key!r} is not valid JSON: {exc}") from exc
