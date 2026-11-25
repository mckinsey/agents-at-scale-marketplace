"""Read workflow files from the file-gateway (story 03).

The engine reads over the file-gateway REST API (``GET /files/{key}/download``),
so it needs no direct volume mount and no S3 credentials — the same gateway the
KYC workflow already uses.

Two loaders:
- :func:`load_output` — the produced output, parsed as JSON.
- :func:`load_input` — the workflow input (e.g. the source email), parsed as
  JSON when possible, otherwise returned as raw text (inputs are often not JSON).
"""

from __future__ import annotations

import json
from typing import Any
from urllib.parse import quote
from urllib.request import urlopen


class OutputError(RuntimeError):
    """A workflow file could not be read or parsed (story 03: clear error)."""


def _download(base_url: str, key: str, timeout_sec: int) -> str:
    """Fetch a file's raw text body from the file-gateway."""
    url = f"{base_url.rstrip('/')}/files/{quote(key, safe='/')}/download"
    try:
        with urlopen(url, timeout=timeout_sec) as resp:  # noqa: S310 — in-cluster URL
            if resp.status != 200:
                raise OutputError(f"file-gateway returned HTTP {resp.status} for {key}")
            return resp.read().decode("utf-8")
    except OutputError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise OutputError(
            f"could not read {key!r} from file-gateway at {base_url}: "
            f"{type(exc).__name__}: {exc}"
        ) from exc


def load_output(base_url: str, key: str, *, timeout_sec: int = 30) -> Any:
    """Download ``key`` and parse it as JSON (the produced output must be JSON)."""
    body = _download(base_url, key, timeout_sec)
    try:
        return json.loads(body)
    except json.JSONDecodeError as exc:
        raise OutputError(f"output {key!r} is not valid JSON: {exc}") from exc


def load_input(base_url: str, key: str, *, timeout_sec: int = 30) -> Any:
    """Download the workflow input, as JSON if parseable else as raw text.

    Inputs are often plain text (an email, a document), so unlike the output we
    do not require JSON: a case with ``source: input`` and ``slice: $`` then
    gets the whole text, and a `regex`/`judge` check works on it directly.
    """
    body = _download(base_url, key, timeout_sec)
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        return body
