"""Tests for broker streaming via stream_chunk in ClaudeAgentExecutor."""

import json

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from claude_agent_sdk.types import AssistantMessage, TextBlock, ThinkingBlock, ToolUseBlock
from ark_sdk.executor import BaseExecutor, Message
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
    async def test_thinking_blocks_not_streamed(self, tmp_path):
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
    async def test_tool_use_blocks_streamed_as_tool_calls(self, tmp_path):
        executor = ClaudeAgentExecutor()
        chunks = []
        tool_calls = []

        async def capture_chunk(text):
            chunks.append(text)

        async def capture_tool_call(name, arguments="", tool_call_id="", index=None):
            tool_calls.append((name, arguments, tool_call_id))

        executor.stream_chunk = capture_chunk
        executor.stream_tool_call = capture_tool_call

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
                yield AssistantMessage(
                    content=[
                        ToolUseBlock(id="toolu_1", name="Bash", input={"command": "ls"}),
                        ToolUseBlock(id="toolu_2", name="Read", input={"path": "/tmp/x"}),
                        TextBlock(text="all done"),
                    ],
                    model="claude-sonnet-4-20250514",
                )
                yield _make_result_message("all done")

        with patch("claude_agent_executor.executor.SESSIONS_DIR", tmp_path), \
             patch("claude_agent_executor.executor.ClaudeSDKClient", FakeClient):
            await executor.execute_agent(_request())

        assert tool_calls == [
            ("Bash", {"command": "ls"}, "toolu_1"),
            ("Read", {"path": "/tmp/x"}, "toolu_2"),
        ]
        assert chunks == ["all done"]

    @pytest.mark.asyncio
    async def test_tool_use_survives_ark_sdk_without_stream_tool_call(self, tmp_path, monkeypatch):
        monkeypatch.delattr(BaseExecutor, "stream_tool_call", raising=False)

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
                yield AssistantMessage(
                    content=[
                        ToolUseBlock(id="toolu_1", name="Bash", input={"command": "ls"}),
                        TextBlock(text="all done"),
                    ],
                    model="claude-sonnet-4-20250514",
                )
                yield _make_result_message("all done")

        with patch("claude_agent_executor.executor.SESSIONS_DIR", tmp_path), \
             patch("claude_agent_executor.executor.ClaudeSDKClient", FakeClient):
            result = await executor.execute_agent(_request())

        assert chunks == ["all done"]
        assert result == [Message(role="assistant", content="all done", name="test-agent")]

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


class TestRealSdkIntegration:
    """Exercises the real BaseExecutor.stream_tool_call rather than a stub, so a
    signature or behaviour change in ark-sdk is caught here instead of in production."""

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not hasattr(BaseExecutor, "stream_tool_call"),
        reason="requires an ark-sdk release providing stream_tool_call",
    )
    async def test_tool_use_reaches_broker_via_real_sdk(self, tmp_path):
        executor = ClaudeAgentExecutor()
        broker = AsyncMock()
        executor._broker_client = broker

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
                yield AssistantMessage(
                    content=[
                        ToolUseBlock(id="toolu_1", name="Bash", input={"command": "ls"}),
                        ToolUseBlock(id="toolu_2", name="Read", input={"path": "/tmp/x"}),
                        TextBlock(text="done"),
                    ],
                    model="claude-sonnet-4-20250514",
                )
                yield _make_result_message("done")

        with patch("claude_agent_executor.executor.SESSIONS_DIR", tmp_path), \
             patch("claude_agent_executor.executor.ClaudeSDKClient", FakeClient):
            await executor.execute_agent(_request())

        tool_calls = [
            call.kwargs["tool_calls"][0]
            for call in broker.send_chunk.await_args_list
            if call.kwargs.get("tool_calls")
        ]

        assert [tc["id"] for tc in tool_calls] == ["toolu_1", "toolu_2"]
        assert [tc["function"]["name"] for tc in tool_calls] == ["Bash", "Read"]
        assert [tc["index"] for tc in tool_calls] == [0, 1]
        assert json.loads(tool_calls[0]["function"]["arguments"]) == {"command": "ls"}
