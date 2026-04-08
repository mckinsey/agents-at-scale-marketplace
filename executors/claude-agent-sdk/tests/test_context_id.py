"""Tests for context_id extraction from A2A JSON-RPC messages."""

import json
import uuid

import pytest

from claude_agent_scheduler.proxy import extract_context_id


def _a2a_message(context_id: str | None = "conv-abc-123", include_field: bool = True) -> bytes:
    """Build a minimal A2A JSON-RPC message body."""
    message: dict = {"role": "user", "parts": [{"text": "hello"}]}  # type: ignore[type-arg]
    if include_field:
        message["context_id"] = context_id
    return json.dumps({
        "jsonrpc": "2.0",
        "method": "message/send",
        "id": "1",
        "params": {"message": message},
    }).encode()


class TestExtractContextId:
    def test_present_context_id(self) -> None:
        cid, body = extract_context_id(_a2a_message("conv-abc-123"))
        assert cid == "conv-abc-123"

    def test_missing_context_id(self) -> None:
        cid, body = extract_context_id(_a2a_message(include_field=False))
        uuid.UUID(cid)
        # Generated ID should be injected into the forwarded body
        data = json.loads(body)
        assert data["params"]["message"]["context_id"] == cid

    def test_empty_context_id(self) -> None:
        cid, body = extract_context_id(_a2a_message(""))
        uuid.UUID(cid)
        data = json.loads(body)
        assert data["params"]["message"]["context_id"] == cid

    def test_whitespace_context_id(self) -> None:
        cid, body = extract_context_id(_a2a_message("   "))
        uuid.UUID(cid)

    def test_null_context_id(self) -> None:
        cid, body = extract_context_id(_a2a_message(None))
        uuid.UUID(cid)

    def test_invalid_json(self) -> None:
        cid, body = extract_context_id(b"not json")
        uuid.UUID(cid)

    def test_context_id_stripped(self) -> None:
        cid, body = extract_context_id(_a2a_message("  conv-123  "))
        assert cid == "conv-123"

    def test_body_unchanged_when_context_id_present(self) -> None:
        original = _a2a_message("conv-existing")
        cid, body = extract_context_id(original)
        assert body is original  # same object, not re-serialized
