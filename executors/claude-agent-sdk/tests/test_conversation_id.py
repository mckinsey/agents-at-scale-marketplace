"""Tests for conversationId validation guarding the session directory join."""

import pytest
from unittest.mock import MagicMock, patch

from claude_agent_executor.executor import (
    SAFE_CONVERSATION_ID,
    ClaudeAgentExecutor,
    resolve_session_dir,
)


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
    "_leading-underscore",
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
    "chat-alice-001",
    "conv-123",
    "550e8400-e29b-41d4-a716-446655440000",
    "a" * 128,
]


def _model_config():
    model = MagicMock()
    model.name = "claude-sonnet-4-20250514"
    model.config = {"anthropic": {"apiKey": "sk-test-key"}}
    return model


def _request(conversation_id):
    request = MagicMock()
    request.conversationId = conversation_id
    request.userInput.content = "hello"
    request.agent.name = "test-agent"
    request.agent.prompt = ""
    request.agent.model = _model_config()
    request.mcpServers = []
    return request


class TestResolveSessionDir:
    @pytest.mark.parametrize("conversation_id", REJECTED)
    def test_rejects_unsafe(self, conversation_id, tmp_path):
        with patch("claude_agent_executor.executor.SESSIONS_DIR", tmp_path):
            with pytest.raises(ValueError):
                resolve_session_dir(conversation_id)

    @pytest.mark.parametrize("conversation_id", ACCEPTED)
    def test_accepts_safe(self, conversation_id, tmp_path):
        with patch("claude_agent_executor.executor.SESSIONS_DIR", tmp_path):
            resolved = resolve_session_dir(conversation_id)

        assert resolved.is_relative_to(tmp_path.resolve())
        assert resolved.name == conversation_id

    def test_rejects_none(self, tmp_path):
        with patch("claude_agent_executor.executor.SESSIONS_DIR", tmp_path):
            with pytest.raises(ValueError):
                resolve_session_dir(None)

    def test_no_directory_created_outside_root(self, tmp_path):
        root = tmp_path / "sessions"
        root.mkdir()
        outside = tmp_path / "outside"

        with patch("claude_agent_executor.executor.SESSIONS_DIR", root):
            with pytest.raises(ValueError):
                resolve_session_dir("../outside")

        assert not outside.exists()


class TestUnthreadedQueriesStillRun:
    """An unset conversationId is the default, not an invalid path segment.

    Query.spec.conversationId is optional and the SDK sends "" when it is unset,
    so validating it unconditionally turned every ordinary one-shot query into
    "Error: invalid conversationId".
    """

    @pytest.mark.asyncio
    @pytest.mark.parametrize("conversation_id", ["", None])
    async def test_unthreaded_runs_in_sessions_root(self, conversation_id, tmp_path):
        executor = ClaudeAgentExecutor.__new__(ClaudeAgentExecutor)
        captured = {}

        class FakeClient:
            def __init__(self, options=None):
                captured["options"] = options

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

            async def query(self, prompt):
                pass

            async def receive_response(self):
                return
                yield

        with patch("claude_agent_executor.executor.SESSIONS_DIR", tmp_path), \
             patch("claude_agent_executor.executor.ClaudeSDKClient", FakeClient):
            messages = await executor.execute_agent(_request(conversation_id))

        assert not any(m.content.startswith("Error:") for m in messages)
        assert captured["options"].cwd == str(tmp_path.resolve())

    @pytest.mark.asyncio
    @pytest.mark.parametrize("conversation_id", ["", None])
    async def test_unthreaded_never_resumes_another_session(self, conversation_id, tmp_path):
        executor = ClaudeAgentExecutor.__new__(ClaudeAgentExecutor)
        captured = {}

        class FakeClient:
            def __init__(self, options=None):
                captured["options"] = options

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

            async def query(self, prompt):
                pass

            async def receive_response(self):
                return
                yield

        stray = MagicMock()
        stray.session_id = "someone-elses-session"

        with patch("claude_agent_executor.executor.SESSIONS_DIR", tmp_path), \
             patch("claude_agent_executor.executor.ClaudeSDKClient", FakeClient), \
             patch("claude_agent_executor.executor.list_sessions", return_value=[stray]) as listed:
            await executor.execute_agent(_request(conversation_id))

        listed.assert_not_called()
        assert getattr(captured["options"], "resume", None) is None


class TestExecuteAgentRejection:
    """The escalation being closed: a rejected id must never reach ClaudeAgentOptions."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("conversation_id", ["/", "..", "../../../tmp/pwned", "/etc/passwd"])
    async def test_rejected_id_never_builds_options(self, conversation_id, tmp_path):
        executor = ClaudeAgentExecutor.__new__(ClaudeAgentExecutor)
        constructed = []

        class FakeClient:
            def __init__(self, options=None):
                constructed.append(options)

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

            async def query(self, prompt):
                pass

            async def receive_response(self):
                return
                yield

        with patch("claude_agent_executor.executor.SESSIONS_DIR", tmp_path), \
             patch("claude_agent_executor.executor.ClaudeSDKClient", FakeClient):
            messages = await executor.execute_agent(_request(conversation_id))

        assert constructed == []
        assert len(messages) == 1
        assert messages[0].content.startswith("Error: invalid conversationId")

    @pytest.mark.asyncio
    async def test_accepted_id_confines_cwd_to_sessions_dir(self, tmp_path):
        executor = ClaudeAgentExecutor.__new__(ClaudeAgentExecutor)
        captured = {}

        class FakeClient:
            def __init__(self, options=None):
                captured["options"] = options

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

            async def query(self, prompt):
                pass

            async def receive_response(self):
                return
                yield

        with patch("claude_agent_executor.executor.SESSIONS_DIR", tmp_path), \
             patch("claude_agent_executor.executor.ClaudeSDKClient", FakeClient):
            await executor.execute_agent(_request("safe-conv-001"))

        cwd = captured["options"].cwd
        assert cwd != "/"
        assert cwd == str(tmp_path.resolve() / "safe-conv-001")


class TestPattern:
    def test_pattern_matches_crd_marker(self):
        assert SAFE_CONVERSATION_ID.pattern == r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,127}$"
