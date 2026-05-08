"""Tests for broker streaming via stream_chunk in ClaudeAgentExecutor."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from claude_agent_sdk.types import AssistantMessage, TextBlock, ThinkingBlock
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


def _make_assistant_message(*texts):
    return AssistantMessage(
        content=[TextBlock(text=t) for t in texts],
        model="claude-sonnet-4-20250514",
    )


def _make_result_message(result="final answer"):
    msg = MagicMock()
    msg.result = result
    return msg


class TestStreaming:
    @pytest.mark.asyncio
    async def test_stream_chunk_called_for_assistant_text_blocks(self, tmp_path):
        executor = ClaudeAgentExecutor()
        chunks = []

        async def capture_chunk(text):
            chunks.append(text)

        executor.stream_chunk = capture_chunk

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
                yield _make_assistant_message("Hello ", "world")
                yield _make_result_message("Hello world")

        with patch("claude_agent_executor.executor.SESSIONS_DIR", tmp_path), \
             patch("claude_agent_executor.executor.ClaudeSDKClient", FakeClient):
            result = await executor.execute_agent(_request())

        assert chunks == ["Hello ", "world"]
        assert result == [Message(role="assistant", content="Hello world", name="test-agent")]

    @pytest.mark.asyncio
    async def test_non_text_blocks_not_streamed(self, tmp_path):
        executor = ClaudeAgentExecutor()
        chunks = []

        async def capture_chunk(text):
            chunks.append(text)

        executor.stream_chunk = capture_chunk

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
                msg = AssistantMessage(
                    content=[
                        ThinkingBlock(thinking="internal thought", signature="sig"),
                        TextBlock(text="visible text"),
                    ],
                    model="claude-sonnet-4-20250514",
                )
                yield msg
                yield _make_result_message("visible text")

        with patch("claude_agent_executor.executor.SESSIONS_DIR", tmp_path), \
             patch("claude_agent_executor.executor.ClaudeSDKClient", FakeClient):
            await executor.execute_agent(_request())

        assert chunks == ["visible text"]

    @pytest.mark.asyncio
    async def test_no_assistant_messages_no_stream_chunks(self, tmp_path):
        executor = ClaudeAgentExecutor()
        chunks = []

        async def capture_chunk(text):
            chunks.append(text)

        executor.stream_chunk = capture_chunk

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
                yield _make_result_message("done")

        with patch("claude_agent_executor.executor.SESSIONS_DIR", tmp_path), \
             patch("claude_agent_executor.executor.ClaudeSDKClient", FakeClient):
            await executor.execute_agent(_request())

        assert chunks == []

    @pytest.mark.asyncio
    async def test_empty_text_blocks_not_streamed(self, tmp_path):
        executor = ClaudeAgentExecutor()
        chunks = []

        async def capture_chunk(text):
            chunks.append(text)

        executor.stream_chunk = capture_chunk

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
                yield _make_assistant_message("")
                yield _make_result_message("done")

        with patch("claude_agent_executor.executor.SESSIONS_DIR", tmp_path), \
             patch("claude_agent_executor.executor.ClaudeSDKClient", FakeClient):
            await executor.execute_agent(_request())

        assert chunks == []
