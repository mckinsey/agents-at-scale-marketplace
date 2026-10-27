"""Invoke an Ark ``Model`` as the judge by creating an Ark ``Query`` (story 03).

Decision (story 03): the judge is called by creating a ``Query`` targeting the
suite's judge ``Model``, not a directly configured gateway — so judge calls are
traced in Langfuse alongside the workflow's own model calls.

Transport is ``kubectl`` (present in the engine image), which keeps the engine
free of the Kubernetes Python client and its auth wiring: in-cluster, the
handler's ServiceAccount already scopes what it may create.
"""

from __future__ import annotations

import json
import subprocess
import time
import uuid

_GROUP = "ark.mckinsey.com"
_VERSION = "v1alpha1"


class QueryError(RuntimeError):
    """Creating, polling, or reading a judge Query failed."""


def ask_model(
    prompt: str,
    *,
    model: str,
    namespace: str,
    timeout_sec: int = 120,
    poll_interval_sec: float = 2.0,
) -> str:
    """Create a Query against ``model``, wait for completion, return its text.

    Raises :class:`QueryError` on creation failure, timeout, or an error phase.
    """
    name = f"eval-judge-{uuid.uuid4().hex[:12]}"
    manifest = {
        "apiVersion": f"{_GROUP}/{_VERSION}",
        "kind": "Query",
        "metadata": {"name": name, "namespace": namespace},
        "spec": {
            "input": prompt,
            "target": {"type": "model", "name": model},
            # Short TTL: judge Queries are ephemeral; let Ark garbage-collect them.
            "ttl": "1h",
        },
    }

    _kubectl_apply(manifest)
    try:
        return _await_response(name, namespace, timeout_sec, poll_interval_sec)
    finally:
        _kubectl_delete(name, namespace)


def _await_response(
    name: str, namespace: str, timeout_sec: int, poll_interval_sec: float
) -> str:
    deadline = time.monotonic() + timeout_sec
    last_phase = "<none>"
    while time.monotonic() < deadline:
        status = _get_status(name, namespace)
        phase = (status or {}).get("phase", "")
        last_phase = phase or last_phase
        if phase == "done":
            response = status.get("response") or {}
            content = response.get("content", "") if isinstance(response, dict) else ""
            if not content:
                raise QueryError(f"judge Query {name} completed with empty response")
            return content
        if phase == "error":
            raise QueryError(f"judge Query {name} ended in error phase")
        time.sleep(poll_interval_sec)
    raise QueryError(
        f"judge Query {name} did not complete within {timeout_sec}s (last phase: {last_phase})"
    )


def _kubectl_apply(manifest: dict) -> None:
    proc = subprocess.run(
        ["kubectl", "apply", "-f", "-"],
        input=json.dumps(manifest),
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise QueryError(f"failed to create judge Query: {proc.stderr.strip()}")


def _get_status(name: str, namespace: str) -> dict:
    proc = subprocess.run(
        ["kubectl", "get", "query", name, "-n", namespace, "-o", "json"],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        return {}
    try:
        return json.loads(proc.stdout).get("status", {}) or {}
    except json.JSONDecodeError:
        return {}


def _kubectl_delete(name: str, namespace: str) -> None:
    subprocess.run(
        ["kubectl", "delete", "query", name, "-n", namespace, "--ignore-not-found"],
        capture_output=True,
        text=True,
    )
