"""Tests for broker streaming via stream_chunk in ClaudeAgentExecutor."""

import pytest
from unittest.mock import MagicMock, patch

from claude_agent_sdk.types import StreamEvent
from ark_sdk.executor import Message
from claude_agent_executor.executor import ClaudeAgentExecutor


def _model_config(name="claude-sonnet-4-20250514", api_key="sk-test"):
    model = MagicMock()
    model.name = name
    model.config = {"anthropic": {"apiKey": api_key}}
    return model


def _request(conversation_id="conv-1", user_input="hello"):
    request = MagicMock()
    request.conversationId = conversation_id
    request.userInput.content = user_input
    request.agent.name = "test-agent"
    request.agent.model = _model_config()
    request.mcpServers = []
    return request


def _text_delta(text):
    return StreamEvent(event={"type": "content_block_delta", "delta": {"type": "text_delta", "text": text}})


def _result_message(result="final answer"):
    msg = MagicMock()
    msg.result = result
    return msg


def _fake_client(*events):
    class FakeClient:
        def __init__(self, options=None):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def query(self, prompt):
            pass

        async def receive_response(self):
            for event in events:
                yield event

    return FakeClient


class TestStreaming:
    @pytest.mark.asyncio
    async def test_stream_chunk_called_for_text_deltas(self, tmp_path):
        executor = ClaudeAgentExecutor()
        chunks = []

        async def capture_chunk(text):
            chunks.append(text)

        executor.stream_chunk = capture_chunk

        FakeClient = _fake_client(
            _text_delta("Hello "),
            _text_delta("world"),
            _result_message("Hello world"),
        )

        with patch("claude_agent_executor.executor.SESSIONS_DIR", tmp_path), \
             patch("claude_agent_executor.executor.ClaudeSDKClient", FakeClient):
            result = await executor.execute_agent(_request())

        assert chunks == ["Hello ", "world"]
        assert result == [Message(role="assistant", content="Hello world", name="test-agent")]

    @pytest.mark.asyncio
    async def test_non_text_delta_events_not_streamed(self, tmp_path):
        executor = ClaudeAgentExecutor()
        chunks = []

        async def capture_chunk(text):
            chunks.append(text)

        executor.stream_chunk = capture_chunk

        FakeClient = _fake_client(
            StreamEvent(event={"type": "message_start"}),
            StreamEvent(event={"type": "content_block_start", "content_block": {"type": "tool_use"}}),
            StreamEvent(event={"type": "content_block_delta", "delta": {"type": "input_json_delta", "partial_json": "{}"}}),
            _text_delta("visible text"),
            StreamEvent(event={"type": "content_block_stop"}),
            _result_message("visible text"),
        )

        with patch("claude_agent_executor.executor.SESSIONS_DIR", tmp_path), \
             patch("claude_agent_executor.executor.ClaudeSDKClient", FakeClient):
            await executor.execute_agent(_request())

        assert chunks == ["visible text"]

    @pytest.mark.asyncio
    async def test_no_stream_events_no_stream_chunks(self, tmp_path):
        executor = ClaudeAgentExecutor()
        chunks = []

        async def capture_chunk(text):
            chunks.append(text)

        executor.stream_chunk = capture_chunk

        FakeClient = _fake_client(_result_message("done"))

        with patch("claude_agent_executor.executor.SESSIONS_DIR", tmp_path), \
             patch("claude_agent_executor.executor.ClaudeSDKClient", FakeClient):
            await executor.execute_agent(_request())

        assert chunks == []

    @pytest.mark.asyncio
    async def test_empty_text_deltas_not_streamed(self, tmp_path):
        executor = ClaudeAgentExecutor()
        chunks = []

        async def capture_chunk(text):
            chunks.append(text)

        executor.stream_chunk = capture_chunk

        FakeClient = _fake_client(
            _text_delta(""),
            _result_message("done"),
        )

        with patch("claude_agent_executor.executor.SESSIONS_DIR", tmp_path), \
             patch("claude_agent_executor.executor.ClaudeSDKClient", FakeClient):
            await executor.execute_agent(_request())

        assert chunks == []
