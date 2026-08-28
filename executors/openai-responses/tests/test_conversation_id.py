"""Tests for conversationId validation guarding the session directory join."""

import pytest
from unittest.mock import patch

from openai_responses_executor import sessions


REJECTED = [
    "/",
    "..",
    "../../../tmp/pwned",
    "/etc/passwd",
    ".",
    "",
    "a/b",
    "a b",
    "a.b",
    ".hidden",
    "-leading-dash",
    "a" * 129,
    "safe-id\n",
    "a" * 128 + "\n",
    "\n",
    "safe-id\n../../etc",
    "safe-id\r\n",
]

ACCEPTED = [
    "a",
    "normal-id",
    "abc_123-XYZ",
    "hitl-demo-conv-001",
    "conv-123",
    "550e8400-e29b-41d4-a716-446655440000",
    "a" * 128,
]


class TestValidateConversationId:
    @pytest.mark.parametrize("conversation_id", REJECTED)
    def test_rejects_unsafe(self, conversation_id):
        with pytest.raises(ValueError):
            sessions.validate_conversation_id(conversation_id)

    @pytest.mark.parametrize("conversation_id", ACCEPTED)
    def test_accepts_safe(self, conversation_id):
        sessions.validate_conversation_id(conversation_id)

    def test_rejects_none(self):
        with pytest.raises(ValueError):
            sessions.validate_conversation_id(None)


class TestConvDir:
    @pytest.mark.parametrize("conversation_id", REJECTED)
    def test_rejects_unsafe(self, conversation_id, tmp_path):
        with patch.object(sessions.config, "sessions_dir", tmp_path):
            with pytest.raises(ValueError):
                sessions._conv_dir(conversation_id)

    def test_confines_to_sessions_dir(self, tmp_path):
        with patch.object(sessions.config, "sessions_dir", tmp_path):
            resolved = sessions._conv_dir("safe-conv-001")

        assert resolved.is_relative_to(tmp_path.resolve())
        assert resolved.name == "safe-conv-001"


class TestWritersRejectTraversal:
    """Every write and unlink path routes through _conv_dir, so all are guarded."""

    @pytest.mark.asyncio
    async def test_save_response_id_rejects(self, tmp_path):
        with patch.object(sessions.config, "sessions_dir", tmp_path):
            with pytest.raises(ValueError):
                await sessions.save_response_id("../pwned", "resp_123")

        assert not (tmp_path.parent / "pwned").exists()

    @pytest.mark.asyncio
    async def test_mark_file_ids_sent_rejects(self, tmp_path):
        with patch.object(sessions.config, "sessions_dir", tmp_path):
            with pytest.raises(ValueError):
                await sessions.mark_file_ids_sent("../pwned", {"file-1"})

        assert not (tmp_path.parent / "pwned").exists()

    @pytest.mark.asyncio
    async def test_clear_conversation_rejects(self, tmp_path):
        with patch.object(sessions.config, "sessions_dir", tmp_path):
            with pytest.raises(ValueError):
                await sessions.clear_conversation("../pwned")

    @pytest.mark.asyncio
    async def test_get_previous_response_id_rejects(self, tmp_path):
        with patch.object(sessions.config, "sessions_dir", tmp_path):
            with pytest.raises(ValueError):
                await sessions.get_previous_response_id("/etc/passwd")

    @pytest.mark.asyncio
    async def test_round_trip_with_safe_id(self, tmp_path):
        with patch.object(sessions.config, "sessions_dir", tmp_path):
            await sessions.save_response_id("safe-conv-001", "resp_123")
            assert await sessions.get_previous_response_id("safe-conv-001") == "resp_123"

            await sessions.mark_file_ids_sent("safe-conv-001", {"file-1"})
            assert await sessions.get_sent_file_ids("safe-conv-001") == {"file-1"}

            await sessions.clear_conversation("safe-conv-001")
            assert await sessions.get_previous_response_id("safe-conv-001") is None
