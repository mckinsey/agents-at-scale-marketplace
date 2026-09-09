"""Tests for the MCP client support (tool discovery, dispatch, prefetch helpers)."""

import logging
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from openai_responses_executor.mcp_tools import (
    _parse_timeout_seconds,
    _sanitize_function_name,
    bindable_dict,
    call_mcp_tool,
    clean_input_text,
    discover_mcp_function_tools,
    function_name_for,
    render_query_template,
)


class _AsyncCM:
    """Minimal async context manager wrapping a fixed value, mirroring the
    real transport/session factories used by mcp_tools (which are called
    synchronously and used with ``async with``)."""

    def __init__(self, value):
        self._value = value

    async def __aenter__(self):
        return self._value

    async def __aexit__(self, *exc):
        return False


def _server(name="my-mcp", url="http://mcp.local", tools=None, transport="http"):
    return SimpleNamespace(name=name, url=url, tools=tools or [], transport=transport, headers={}, timeout=None)


def _tool(name):
    return SimpleNamespace(name=name, description=f"{name} description", inputSchema={"type": "object", "properties": {}})


# ---------------------------------------------------------------------------
# Pure helpers (kept to the ones with real branching, not straight passthrough)
# ---------------------------------------------------------------------------


class TestParseTimeoutSeconds:
    def test_go_duration_string_delegates_to_ark_sdk(self):
        assert _parse_timeout_seconds("1m30s") == 90.0

    def test_falls_back_to_manual_parsing_when_ark_sdk_raises(self):
        with patch("ark_sdk.extensions.query._parse_go_duration_to_seconds", side_effect=Exception("boom")):
            assert _parse_timeout_seconds("1m30s") == 90.0


class TestSanitizeFunctionName:
    def test_replaces_disallowed_characters(self):
        assert _sanitize_function_name("my server/tool!") == "my_server_tool_"


class TestFunctionNameFor:
    def test_joins_server_and_tool(self):
        assert function_name_for("weather-mcp", "get-forecast") == "weather-mcp__get-forecast"


class TestRenderQueryTemplate:
    def test_drops_unresolved_placeholders_and_collapses_whitespace(self):
        result = render_query_template("a {input}   {ch.locality}  b", {"input": "x"})
        assert result == "a x b"


class TestBindableDict:
    def test_unwraps_lone_result_key(self):
        assert bindable_dict({"result": {"a": 1}}) == {"a": 1}


class TestCleanInputText:
    def test_extracts_last_message_content_from_chat_array(self):
        raw = '[{"role": "user", "content": "hello there"}]'
        assert clean_input_text(raw) == "hello there"


# ---------------------------------------------------------------------------
# discover_mcp_function_tools — where the real prod bug (renamed
# streamablehttp_client under mcp 2.x) lived, so this gets the most coverage.
# ---------------------------------------------------------------------------


class TestDiscoverMcpFunctionTools:
    @pytest.mark.asyncio
    async def test_server_with_no_declared_tools_is_skipped_without_connecting(self):
        with patch("mcp.ClientSession") as mock_session_cls:
            function_tools, registry = await discover_mcp_function_tools([_server(tools=[])])

        assert function_tools == []
        assert registry == {}
        mock_session_cls.assert_not_called()

    @pytest.mark.asyncio
    async def test_matched_tool_is_exposed_and_registered(self):
        session = MagicMock()
        session.initialize = AsyncMock()
        session.list_tools = AsyncMock(return_value=SimpleNamespace(tools=[_tool("search")]))

        with patch("mcp.client.streamable_http.streamablehttp_client",
                   return_value=_AsyncCM((MagicMock(), MagicMock(), lambda: "id"))), \
             patch("mcp.ClientSession", return_value=_AsyncCM(session)):
            function_tools, registry = await discover_mcp_function_tools(
                [_server(name="weather", tools=["search"])]
            )

        session.list_tools.assert_awaited_once()
        assert function_tools == [{
            "type": "function",
            "name": "weather__search",
            "description": "search description",
            "parameters": {"type": "object", "properties": {}},
        }]
        assert registry["weather__search"][1] == "search"

    @pytest.mark.asyncio
    async def test_allow_list_matching_is_hyphen_underscore_insensitive(self):
        session = MagicMock()
        session.initialize = AsyncMock()
        session.list_tools = AsyncMock(return_value=SimpleNamespace(tools=[_tool("get-forecast")]))

        with patch("mcp.client.streamable_http.streamablehttp_client",
                   return_value=_AsyncCM((MagicMock(), MagicMock(), lambda: "id"))), \
             patch("mcp.ClientSession", return_value=_AsyncCM(session)):
            function_tools, _ = await discover_mcp_function_tools(
                [_server(name="weather", tools=["get_forecast"])]
            )

        assert len(function_tools) == 1

    @pytest.mark.asyncio
    async def test_unmatched_available_tools_are_not_exposed(self):
        session = MagicMock()
        session.initialize = AsyncMock()
        session.list_tools = AsyncMock(return_value=SimpleNamespace(tools=[_tool("other-tool")]))

        with patch("mcp.client.streamable_http.streamablehttp_client",
                   return_value=_AsyncCM((MagicMock(), MagicMock(), lambda: "id"))), \
             patch("mcp.ClientSession", return_value=_AsyncCM(session)):
            function_tools, registry = await discover_mcp_function_tools(
                [_server(name="weather", tools=["search"])]
            )

        assert function_tools == []
        assert registry == {}

    @pytest.mark.asyncio
    async def test_connection_failure_is_logged_and_server_is_skipped(self, caplog):
        with patch("mcp.client.streamable_http.streamablehttp_client", side_effect=RuntimeError("connection refused")):
            with caplog.at_level(logging.WARNING):
                function_tools, registry = await discover_mcp_function_tools(
                    [_server(name="flaky-server", tools=["search"])]
                )

        assert function_tools == []
        assert registry == {}
        assert any("flaky-server" in record.message for record in caplog.records)


# ---------------------------------------------------------------------------
# call_mcp_tool
# ---------------------------------------------------------------------------


class TestCallMcpTool:
    @pytest.mark.asyncio
    async def test_unwraps_structured_content(self):
        session = MagicMock()
        session.initialize = AsyncMock()
        result = SimpleNamespace(isError=False, structuredContent={"result": {"temp": 72}}, content=[])
        session.call_tool = AsyncMock(return_value=result)

        with patch("mcp.client.streamable_http.streamablehttp_client",
                   return_value=_AsyncCM((MagicMock(), MagicMock(), lambda: "id"))), \
             patch("mcp.ClientSession", return_value=_AsyncCM(session)):
            value = await call_mcp_tool(_server(), "get_weather", {"city": "nyc"})

        session.call_tool.assert_awaited_once_with("get_weather", arguments={"city": "nyc"})
        assert value == {"temp": 72}

    @pytest.mark.asyncio
    async def test_falls_back_to_text_content_blocks(self):
        session = MagicMock()
        session.initialize = AsyncMock()
        result = SimpleNamespace(
            isError=False,
            structuredContent=None,
            content=[SimpleNamespace(text="hello", type="text"), SimpleNamespace(text="world", type="text")],
        )
        session.call_tool = AsyncMock(return_value=result)

        with patch("mcp.client.streamable_http.streamablehttp_client",
                   return_value=_AsyncCM((MagicMock(), MagicMock(), lambda: "id"))), \
             patch("mcp.ClientSession", return_value=_AsyncCM(session)):
            value = await call_mcp_tool(_server(), "echo", {})

        assert value == {"content": "hello\nworld"}

    @pytest.mark.asyncio
    async def test_is_error_flag_wraps_result_as_error(self):
        session = MagicMock()
        session.initialize = AsyncMock()
        result = SimpleNamespace(isError=True, structuredContent={"reason": "bad input"}, content=[])
        session.call_tool = AsyncMock(return_value=result)

        with patch("mcp.client.streamable_http.streamablehttp_client",
                   return_value=_AsyncCM((MagicMock(), MagicMock(), lambda: "id"))), \
             patch("mcp.ClientSession", return_value=_AsyncCM(session)):
            value = await call_mcp_tool(_server(), "get_weather", {})

        assert value == {"error": {"reason": "bad input"}}

    @pytest.mark.asyncio
    async def test_session_exception_returns_error_dict(self):
        with patch("mcp.client.streamable_http.streamablehttp_client", side_effect=RuntimeError("unreachable")):
            value = await call_mcp_tool(_server(), "get_weather", {})

        assert value == {"error": "MCP tool 'get_weather' call failed: unreachable"}
