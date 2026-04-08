"""Tests for context_id extraction from A2A JSON (Task 8.2)."""

import json
import uuid

import pytest

from claude_agent_scheduler.proxy import extract_context_id


class TestExtractContextId:
    def test_present_context_id(self) -> None:
        body = json.dumps({"context_id": "conv-abc-123", "message": {"role": "user"}}).encode()
        assert extract_context_id(body) == "conv-abc-123"

    def test_missing_context_id(self) -> None:
        body = json.dumps({"message": {"role": "user"}}).encode()
        result = extract_context_id(body)
        # Should generate a valid UUID
        uuid.UUID(result)

    def test_empty_context_id(self) -> None:
        body = json.dumps({"context_id": "", "message": {"role": "user"}}).encode()
        result = extract_context_id(body)
        uuid.UUID(result)

    def test_whitespace_context_id(self) -> None:
        body = json.dumps({"context_id": "   ", "message": {"role": "user"}}).encode()
        result = extract_context_id(body)
        uuid.UUID(result)

    def test_null_context_id(self) -> None:
        body = json.dumps({"context_id": None}).encode()
        result = extract_context_id(body)
        uuid.UUID(result)

    def test_invalid_json(self) -> None:
        body = b"not json"
        result = extract_context_id(body)
        uuid.UUID(result)

    def test_context_id_stripped(self) -> None:
        body = json.dumps({"context_id": "  conv-123  "}).encode()
        assert extract_context_id(body) == "conv-123"
