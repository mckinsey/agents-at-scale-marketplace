"""Tests for contextId extraction and UUID4 validation."""

import json
import uuid

import pytest

from claude_agent_scheduler.proxy import extract_context_id


def _a2a_message(context_id: str | None = None, include_field: bool = True) -> bytes:
    """Build a minimal A2A JSON-RPC request body."""
    message: dict = {"role": "user", "parts": [{"text": "hello"}]}  # type: ignore[type-arg]
    if include_field:
        message["contextId"] = context_id
    return json.dumps({
        "jsonrpc": "2.0",
        "method": "message/send",
        "id": "1",
        "params": {"message": message},
    }).encode()


class TestExtractContextId:
    def test_valid_uuid4_passes_through(self) -> None:
        test_uuid = str(uuid.uuid4())
        cid, body, is_new = extract_context_id(_a2a_message(test_uuid))
        assert cid == test_uuid
        assert is_new is False

    def test_missing_generates_uuid4_and_injects(self) -> None:
        cid, body, is_new = extract_context_id(_a2a_message(include_field=False))
        uuid.UUID(cid, version=4)  # validates format
        assert is_new is True
        data = json.loads(body)
        assert data["params"]["message"]["contextId"] == cid

    def test_empty_generates_uuid4_and_injects(self) -> None:
        cid, body, is_new = extract_context_id(_a2a_message(""))
        uuid.UUID(cid, version=4)
        assert is_new is True
        data = json.loads(body)
        assert data["params"]["message"]["contextId"] == cid

    def test_whitespace_generates_uuid4(self) -> None:
        cid, _, is_new = extract_context_id(_a2a_message("   "))
        uuid.UUID(cid, version=4)
        assert is_new is True

    def test_null_generates_uuid4(self) -> None:
        cid, _, is_new = extract_context_id(_a2a_message(None))
        uuid.UUID(cid, version=4)
        assert is_new is True

    def test_invalid_json_generates_uuid4(self) -> None:
        cid, _, is_new = extract_context_id(b"not json")
        uuid.UUID(cid, version=4)
        assert is_new is True

    def test_non_uuid4_string_raises_valueerror(self) -> None:
        with pytest.raises(ValueError, match="Invalid contextId"):
            extract_context_id(_a2a_message("my-custom-session-id"))

    def test_uuid5_rejected(self) -> None:
        test_uuid5 = str(uuid.uuid5(uuid.NAMESPACE_URL, "test"))
        with pytest.raises(ValueError, match="Invalid contextId"):
            extract_context_id(_a2a_message(test_uuid5))

    def test_dots_and_special_chars_rejected(self) -> None:
        with pytest.raises(ValueError, match="Invalid contextId"):
            extract_context_id(_a2a_message("user@example.com/session:42"))

    def test_body_unchanged_when_valid_uuid4(self) -> None:
        test_uuid = str(uuid.uuid4())
        original = _a2a_message(test_uuid)
        cid, body, is_new = extract_context_id(original)
        assert body is original
        assert is_new is False
