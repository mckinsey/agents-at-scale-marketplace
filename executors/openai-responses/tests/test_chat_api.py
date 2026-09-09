"""Tests for the SSE /chat endpoint used by the file-assistant UI."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from openai_responses_executor import chat_api
from openai_responses_executor.agent_credentials import AgentContext


class _AsyncCM:
    def __init__(self, value):
        self._value = value

    async def __aenter__(self):
        return self._value

    async def __aexit__(self, *exc):
        return False


class _FakeStream:
    """Mimics the async-iterable + get_final_response shape of client.responses.stream()."""

    def __init__(self, events, final_response):
        self._events = events
        self._final = final_response

    def __aiter__(self):
        return self

    async def __anext__(self):
        if not self._events:
            raise StopAsyncIteration
        return self._events.pop(0)

    async def get_final_response(self):
        return self._final


def _request(query_params=None, body=None):
    request = MagicMock()
    request.query_params = query_params or {}
    request.json = AsyncMock(return_value=body if body is not None else {})
    return request


async def _collect(agen):
    return [chunk async for chunk in agen]


class TestEnvContext:
    def test_raises_when_no_api_key_configured(self):
        # Guards against silently starting a chat with no credentials at all.
        with patch.object(chat_api.config, "openai_api_key", ""):
            with pytest.raises(ValueError, match="No API key configured"):
                chat_api._env_context()


class TestResolveContext:
    @pytest.mark.asyncio
    async def test_no_agent_param_uses_env_context(self):
        env_ctx = AgentContext(api_key="sk-env", base_url=None, model_name="m", instructions="i")
        with patch.object(chat_api, "_env_context", return_value=env_ctx):
            assert await chat_api._resolve_context(_request()) is env_ctx

    @pytest.mark.asyncio
    async def test_agent_param_resolves_via_agent_credentials(self):
        agent_ctx = AgentContext(api_key="sk-agent", base_url=None, model_name="m", instructions="i")
        with patch.object(chat_api, "resolve_agent_context", AsyncMock(return_value=agent_ctx)) as mock_resolve:
            ctx = await chat_api._resolve_context(_request(query_params={"agent": "team-a/my-agent"}))

        mock_resolve.assert_awaited_once_with("my-agent", "team-a")
        assert ctx is agent_ctx

    @pytest.mark.asyncio
    async def test_agent_that_fails_to_resolve_raises_without_env_fallback(self):
        # An explicit ?agent= must never silently fall back to the (wrong)
        # cluster-wide OpenAI project.
        with patch.object(chat_api, "resolve_agent_context", AsyncMock(return_value=None)), \
             patch.object(chat_api, "_env_context") as mock_env:
            with pytest.raises(ValueError, match="no OpenAI model configured"):
                await chat_api._resolve_context(_request(query_params={"agent": "team-a/my-agent"}))

        mock_env.assert_not_called()


class TestFileIdsFor:
    @pytest.mark.asyncio
    async def test_lists_files_for_the_requested_agent(self):
        mock_index = MagicMock()
        mock_index.list_for_agent.return_value = ["file-1"]
        with patch.object(chat_api, "get_index", return_value=mock_index):
            ids = await chat_api._file_ids_for(_request(query_params={"agent": "team-a/my-agent"}))

        mock_index.list_for_agent.assert_called_once_with("my-agent")
        assert ids == ["file-1"]

    @pytest.mark.asyncio
    async def test_index_failure_degrades_to_empty_list(self):
        with patch.object(chat_api, "get_index", side_effect=RuntimeError("disk error")):
            assert await chat_api._file_ids_for(_request()) == []


class TestChatEndpointValidation:
    @pytest.mark.asyncio
    async def test_missing_message_returns_400(self):
        response = await chat_api.chat(_request(body={"conversationId": "c1"}))
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_invalid_conversation_id_returns_400(self):
        response = await chat_api.chat(_request(body={"message": "hi", "conversationId": "../etc"}))
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_context_resolution_failure_returns_400(self):
        request = _request(body={"message": "hi", "conversationId": "conv-1"})
        with patch.object(chat_api, "_resolve_context", AsyncMock(side_effect=ValueError("no model"))):
            response = await chat_api.chat(request)

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_explicit_file_ids_in_body_skip_index_lookup(self):
        ctx = AgentContext(api_key="sk", base_url=None, model_name="m", instructions="i")
        request = _request(body={
            "message": "hi", "conversationId": "conv-1", "file_ids": ["file-1", 123, "file-2"],
        })
        with patch.object(chat_api, "_resolve_context", AsyncMock(return_value=ctx)), \
             patch.object(chat_api, "_file_ids_for", AsyncMock()) as mock_file_ids, \
             patch.object(chat_api, "_stream_chat") as mock_stream:
            mock_stream.return_value = iter([])
            await chat_api.chat(request)

        mock_file_ids.assert_not_awaited()
        mock_stream.assert_called_once_with(ctx, "hi", "conv-1", ["file-1", "file-2"])


class TestResetChat:
    @pytest.mark.asyncio
    async def test_invalid_conversation_id_returns_400(self):
        response = await chat_api.reset_chat(_request(body={"conversationId": "../etc"}))
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_clears_conversation_and_confirms(self):
        with patch.object(chat_api.sessions, "clear_conversation", AsyncMock()) as mock_clear:
            response = await chat_api.reset_chat(_request(body={"conversationId": "conv-1"}))

        mock_clear.assert_awaited_once_with("conv-1")
        assert response.status_code == 200


class TestStreamChat:
    def _ctx(self):
        return AgentContext(api_key="sk", base_url=None, model_name="gpt-4o", instructions="be helpful")

    @pytest.mark.asyncio
    async def test_streams_deltas_and_saves_response_id(self):
        events = [MagicMock(type="response.output_text.delta", delta="hel"), MagicMock(type="response.output_text.delta", delta="lo")]
        final = MagicMock(id="resp-1")
        fake_client = MagicMock()
        fake_client.responses.stream = MagicMock(return_value=_AsyncCM(_FakeStream(events, final)))

        with patch.object(chat_api, "client_for", return_value=fake_client), \
             patch.object(chat_api.sessions, "get_previous_response_id", AsyncMock(return_value=None)), \
             patch.object(chat_api.sessions, "save_response_id", AsyncMock()) as mock_save, \
             patch.object(chat_api.sessions, "mark_file_ids_sent", AsyncMock()) as mock_mark:
            chunks = await _collect(chat_api._stream_chat(self._ctx(), "hi", "conv-1", ["file-1"]))

        mock_save.assert_awaited_once_with("conv-1", "resp-1")
        mock_mark.assert_awaited_once_with("conv-1", {"file-1"})
        assert any('"type": "delta"' in c and '"text": "hel"' in c for c in chunks)
        assert any('"type": "done"' in c for c in chunks)

    @pytest.mark.asyncio
    async def test_skips_files_already_attached_in_earlier_turn(self):
        final = MagicMock(id="resp-2")
        fake_client = MagicMock()
        fake_client.responses.stream = MagicMock(return_value=_AsyncCM(_FakeStream([], final)))

        with patch.object(chat_api, "client_for", return_value=fake_client), \
             patch.object(chat_api.sessions, "get_previous_response_id", AsyncMock(return_value="resp-1")), \
             patch.object(chat_api.sessions, "get_sent_file_ids", AsyncMock(return_value={"file-1"})), \
             patch.object(chat_api.sessions, "save_response_id", AsyncMock()), \
             patch.object(chat_api.sessions, "mark_file_ids_sent", AsyncMock()) as mock_mark:
            chunks = await _collect(chat_api._stream_chat(self._ctx(), "hi", "conv-1", ["file-1", "file-2"]))

        mock_mark.assert_awaited_once_with("conv-1", {"file-2"})
        assert any('"file_ids": ["file-2"]' in c for c in chunks)

    @pytest.mark.asyncio
    async def test_zdr_error_clears_conversation_and_emits_hint(self):
        fake_client = MagicMock()
        fake_client.responses.stream = MagicMock(side_effect=RuntimeError(
            "previous_response_id not supported: organization enforces Zero Data Retention"
        ))

        with patch.object(chat_api, "client_for", return_value=fake_client), \
             patch.object(chat_api.sessions, "get_previous_response_id", AsyncMock(return_value=None)), \
             patch.object(chat_api.sessions, "clear_conversation", AsyncMock()) as mock_clear:
            chunks = await _collect(chat_api._stream_chat(self._ctx(), "hi", "conv-1", []))

        mock_clear.assert_awaited_once_with("conv-1")
        assert any("Zero Data Retention" in c and "provider error" in c for c in chunks)

    @pytest.mark.asyncio
    async def test_generic_provider_error_is_surfaced_without_clearing_conversation(self):
        fake_client = MagicMock()
        fake_client.responses.stream = MagicMock(side_effect=RuntimeError("upstream 500"))

        with patch.object(chat_api, "client_for", return_value=fake_client), \
             patch.object(chat_api.sessions, "get_previous_response_id", AsyncMock(return_value=None)), \
             patch.object(chat_api.sessions, "clear_conversation", AsyncMock()) as mock_clear:
            chunks = await _collect(chat_api._stream_chat(self._ctx(), "hi", "conv-1", []))

        mock_clear.assert_not_awaited()
        assert any('"error": "upstream 500"' in c for c in chunks)
