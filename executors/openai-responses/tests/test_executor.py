"""Unit tests for OpenAI Responses API executor."""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from ark_sdk.executor import Message, ToolDefinition
from openai_responses_executor.executor import OpenAIResponsesExecutor
from openai_responses_executor.models import WebSearchUserLocation


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _model_config(name="gpt-4o", api_key="sk-test-key", base_url=None):
    """Build a mock model object matching Model CRD structure."""
    openai_cfg = {"apiKey": api_key}
    if base_url is not None:
        openai_cfg["baseUrl"] = base_url
    model = MagicMock()
    model.name = name
    model.config = {"openai": openai_cfg}
    return model


def _tool(name="search", description="Search the web", parameters=None):
    return ToolDefinition(
        name=name,
        description=description,
        parameters=parameters or {"type": "object", "properties": {"query": {"type": "string"}}},
    )


def _request(
    agent_name="test-agent",
    model=None,
    labels=None,
    tools=None,
    history=None,
    conversation_id="conv-123",
    user_content="hello",
):
    req = MagicMock()
    req.agent.name = agent_name
    req.agent.model = model or _model_config()
    req.agent.labels = labels or {}
    req.agent.prompt = "You are a helpful assistant."
    req.agent.parameters = []
    req.tools = tools or []
    req.history = history or []
    req.userInput.content = user_content
    req.conversationId = conversation_id
    req.tools_config = None  # populated once Query CR supports spec.tools
    return req


# ---------------------------------------------------------------------------
# _resolve_model_config
# ---------------------------------------------------------------------------


class TestResolveModelConfig:
    def test_valid_openai_config(self):
        req = _request(model=_model_config("gpt-4o", "sk-abc", "https://proxy.example.com"))
        model_name, api_key, base_url = OpenAIResponsesExecutor._resolve_model_config(req)

        assert model_name == "gpt-4o"
        assert api_key == "sk-abc"
        assert base_url == "https://proxy.example.com"

    def test_no_base_url(self):
        req = _request(model=_model_config("gpt-4o", "sk-abc"))
        model_name, api_key, base_url = OpenAIResponsesExecutor._resolve_model_config(req)

        assert model_name == "gpt-4o"
        assert api_key == "sk-abc"
        assert base_url is None

    def test_missing_openai_config_raises(self):
        req = _request()
        req.agent.model.config = {"anthropic": {"apiKey": "sk-ant"}}

        with pytest.raises(ValueError, match="provider 'openai'"):
            OpenAIResponsesExecutor._resolve_model_config(req)

    def test_missing_api_key_raises(self):
        req = _request()
        req.agent.model.config = {"openai": {"baseUrl": "https://proxy.example.com"}}

        with pytest.raises(ValueError, match="apiKey"):
            OpenAIResponsesExecutor._resolve_model_config(req)

    def test_no_model_raises(self):
        req = _request()
        req.agent.model = None

        with pytest.raises(ValueError, match="model"):
            OpenAIResponsesExecutor._resolve_model_config(req)


# ---------------------------------------------------------------------------
# _build_function_tools
# ---------------------------------------------------------------------------


class TestBuildFunctionTools:
    def test_single_tool(self):
        tools = [_tool("search", "Search the web")]
        result = OpenAIResponsesExecutor._build_function_tools(tools)

        assert len(result) == 1
        assert result[0]["type"] == "function"
        assert result[0]["name"] == "search"
        assert result[0]["description"] == "Search the web"
        assert "parameters" in result[0]

    def test_empty_tools(self):
        result = OpenAIResponsesExecutor._build_function_tools([])
        assert result == []

    def test_tool_without_parameters_gets_defaults(self):
        tool = ToolDefinition(name="ping", description="Ping something", parameters={})
        result = OpenAIResponsesExecutor._build_function_tools([tool])

        assert result[0]["parameters"] == {"type": "object", "properties": {}}


# ---------------------------------------------------------------------------
# _get_built_in_tools
# ---------------------------------------------------------------------------


class TestGetWebSearchUserLocation:
    def _param(self, name, value):
        p = MagicMock()
        p.name = name
        p.value = value
        return p

    def test_full_location(self):
        req = _request()
        req.agent.parameters = [
            self._param("openai.web-search.country", "GB"),
            self._param("openai.web-search.city", "London"),
            self._param("openai.web-search.region", "London"),
        ]
        result = OpenAIResponsesExecutor._get_web_search_user_location(req)

        assert isinstance(result, WebSearchUserLocation)
        assert result.country == "GB"
        assert result.city == "London"
        assert result.region == "London"

    def test_country_only(self):
        req = _request()
        req.agent.parameters = [self._param("openai.web-search.country", "US")]
        result = OpenAIResponsesExecutor._get_web_search_user_location(req)

        assert isinstance(result, WebSearchUserLocation)
        assert result.country == "US"
        assert result.city is None

    def test_no_location_params_returns_none(self):
        req = _request()
        req.agent.parameters = []
        result = OpenAIResponsesExecutor._get_web_search_user_location(req)
        assert result is None


class TestGetBuiltInTools:
    def test_web_search_enabled(self):
        req = _request(labels={"ark.openai.tools/web-search-preview": "true"})
        result = OpenAIResponsesExecutor._get_built_in_tools(req)

        assert {"type": "web_search_preview"} in result

    def test_web_search_with_user_location(self):
        p = MagicMock()
        p.name = "openai.web-search.country"
        p.value = "GB"
        req = _request(labels={"ark.openai.tools/web-search-preview": "true"})
        req.agent.parameters = [p]
        result = OpenAIResponsesExecutor._get_built_in_tools(req)

        assert len(result) == 1
        assert result[0]["type"] == "web_search_preview"
        # model_dump(exclude_none=True) omits None fields
        assert result[0]["user_location"] == {"type": "approximate", "country": "GB"}

    def test_multiple_built_in_tools(self):
        req = _request(
            labels={
                "ark.openai.tools/web-search-preview": "true",
                "ark.openai.tools/code-interpreter": "true",
            }
        )
        result = OpenAIResponsesExecutor._get_built_in_tools(req)

        types = [t["type"] for t in result]
        assert "web_search_preview" in types
        assert "code_interpreter" in types

    def test_no_labels_returns_empty(self):
        req = _request(labels={})
        result = OpenAIResponsesExecutor._get_built_in_tools(req)
        assert result == []

    def test_label_value_false_not_included(self):
        req = _request(labels={"ark.openai.tools/web-search-preview": "false"})
        result = OpenAIResponsesExecutor._get_built_in_tools(req)
        assert result == []

    def test_file_search_and_computer_use(self):
        req = _request(
            labels={
                "ark.openai.tools/file-search": "true",
                "ark.openai.tools/computer-use-preview": "true",
            }
        )
        result = OpenAIResponsesExecutor._get_built_in_tools(req)
        types = [t["type"] for t in result]
        assert "file_search" in types
        assert "computer_use_preview" in types


# ---------------------------------------------------------------------------
# _build_first_turn_input
# ---------------------------------------------------------------------------


class TestBuildFirstTurnInput:
    def test_no_history(self):
        req = _request(history=[], user_content="what is 2+2?")
        result = OpenAIResponsesExecutor._build_first_turn_input(req)

        assert result == [{"role": "user", "content": "what is 2+2?"}]

    def test_with_history(self):
        history = [
            Message(role="user", content="hi"),
            Message(role="assistant", content="hello"),
        ]
        req = _request(history=history, user_content="what is 2+2?")
        result = OpenAIResponsesExecutor._build_first_turn_input(req)

        assert len(result) == 3
        assert result[0] == {"role": "user", "content": "hi"}
        assert result[1] == {"role": "assistant", "content": "hello"}
        assert result[2] == {"role": "user", "content": "what is 2+2?"}


# ---------------------------------------------------------------------------
# _extract_text_output
# ---------------------------------------------------------------------------


class TestExtractTextOutput:
    def _make_response(self, text):
        content_part = MagicMock()
        content_part.type = "output_text"
        content_part.text = text

        message_item = MagicMock()
        message_item.type = "message"
        message_item.content = [content_part]

        response = MagicMock()
        response.output = [message_item]
        return response

    def test_extracts_text(self):
        response = self._make_response("Hello, world!")
        assert OpenAIResponsesExecutor._extract_text_output(response) == "Hello, world!"

    def test_no_message_item_returns_none(self):
        item = MagicMock()
        item.type = "function_call"
        response = MagicMock()
        response.output = [item]
        assert OpenAIResponsesExecutor._extract_text_output(response) is None


# ---------------------------------------------------------------------------
# _extract_function_calls
# ---------------------------------------------------------------------------


class TestExtractFunctionCalls:
    def test_returns_function_calls(self):
        fc = MagicMock()
        fc.type = "function_call"
        other = MagicMock()
        other.type = "message"
        response = MagicMock()
        response.output = [fc, other]

        result = OpenAIResponsesExecutor._extract_function_calls(response)
        assert result == [fc]

    def test_no_function_calls(self):
        item = MagicMock()
        item.type = "message"
        response = MagicMock()
        response.output = [item]

        assert OpenAIResponsesExecutor._extract_function_calls(response) == []


# ---------------------------------------------------------------------------
# Session helpers
# ---------------------------------------------------------------------------


class TestSessionHelpers:
    def test_save_and_get_response_id(self, tmp_path):
        with patch("openai_responses_executor.executor.SESSIONS_DIR", tmp_path):
            OpenAIResponsesExecutor._save_response_id("conv-1", "resp-abc123")
            result = OpenAIResponsesExecutor._get_previous_response_id("conv-1")
        assert result == "resp-abc123"

    def test_get_response_id_missing_returns_none(self, tmp_path):
        with patch("openai_responses_executor.executor.SESSIONS_DIR", tmp_path):
            result = OpenAIResponsesExecutor._get_previous_response_id("conv-nonexistent")
        assert result is None


# ---------------------------------------------------------------------------
# execute_agent — integration-style unit tests with mocked OpenAI client
# ---------------------------------------------------------------------------


def _make_text_response(text="Test response", response_id="resp-001"):
    content_part = MagicMock()
    content_part.type = "output_text"
    content_part.text = text

    message_item = MagicMock()
    message_item.type = "message"
    message_item.content = [content_part]

    response = MagicMock()
    response.id = response_id
    response.output = [message_item]
    return response


def _make_function_call_response(name, arguments, call_id, response_id="resp-tool-001"):
    fc_item = MagicMock()
    fc_item.type = "function_call"
    fc_item.name = name
    fc_item.arguments = json.dumps(arguments)
    fc_item.call_id = call_id

    response = MagicMock()
    response.id = response_id
    response.output = [fc_item]
    return response


class TestExecuteAgent:
    @pytest.mark.asyncio
    async def test_simple_text_response(self, tmp_path):
        executor = OpenAIResponsesExecutor.__new__(OpenAIResponsesExecutor)
        req = _request()

        mock_response = _make_text_response("Paris is the capital of France.")

        mock_client = AsyncMock()
        mock_client.responses.create = AsyncMock(return_value=mock_response)

        with patch("openai_responses_executor.executor.SESSIONS_DIR", tmp_path), \
             patch("openai_responses_executor.executor.AsyncOpenAI", return_value=mock_client):
            messages = await executor.execute_agent(req)

        assert len(messages) == 1
        assert messages[0].role == "assistant"
        assert messages[0].content == "Paris is the capital of France."
        assert messages[0].name == "test-agent"

    @pytest.mark.asyncio
    async def test_uses_previous_response_id_on_second_turn(self, tmp_path):
        executor = OpenAIResponsesExecutor.__new__(OpenAIResponsesExecutor)
        req = _request()

        # Pre-seed a saved response ID (simulating a previous turn)
        session_dir = tmp_path / "conv-123"
        session_dir.mkdir()
        (session_dir / "response_id").write_text("resp-prev-001")

        mock_response = _make_text_response("Follow-up answer.")
        mock_client = AsyncMock()
        mock_client.responses.create = AsyncMock(return_value=mock_response)

        captured_kwargs = {}

        async def capture_create(**kwargs):
            captured_kwargs.update(kwargs)
            return mock_response

        mock_client.responses.create = capture_create

        with patch("openai_responses_executor.executor.SESSIONS_DIR", tmp_path), \
             patch("openai_responses_executor.executor.AsyncOpenAI", return_value=mock_client):
            await executor.execute_agent(req)

        assert captured_kwargs.get("previous_response_id") == "resp-prev-001"
        # On second turn, input should be just the user string, not the full history list
        assert captured_kwargs.get("input") == "hello"

    @pytest.mark.asyncio
    async def test_saves_response_id_after_call(self, tmp_path):
        executor = OpenAIResponsesExecutor.__new__(OpenAIResponsesExecutor)
        req = _request()

        mock_response = _make_text_response("Some answer.", response_id="resp-saved-001")
        mock_client = AsyncMock()
        mock_client.responses.create = AsyncMock(return_value=mock_response)

        with patch("openai_responses_executor.executor.SESSIONS_DIR", tmp_path), \
             patch("openai_responses_executor.executor.AsyncOpenAI", return_value=mock_client):
            await executor.execute_agent(req)

        saved = (tmp_path / "conv-123" / "response_id").read_text()
        assert saved == "resp-saved-001"

    @pytest.mark.asyncio
    async def test_function_call_loop(self, tmp_path):
        """Executor should call the tool and continue with a follow-up response."""
        executor = OpenAIResponsesExecutor.__new__(OpenAIResponsesExecutor)
        req = _request(tools=[_tool("search", "Search the web")])

        tool_response = _make_function_call_response("search", {"query": "python"}, "call-001", "resp-tool-001")
        final_response = _make_text_response("Python is a programming language.", "resp-final-001")

        call_count = 0

        async def mock_create(**kwargs):
            nonlocal call_count
            call_count += 1
            return tool_response if call_count == 1 else final_response

        mock_client = AsyncMock()
        mock_client.responses.create = mock_create

        with patch("openai_responses_executor.executor.SESSIONS_DIR", tmp_path), \
             patch("openai_responses_executor.executor.AsyncOpenAI", return_value=mock_client):
            messages = await executor.execute_agent(req)

        assert call_count == 2
        assert messages[0].content == "Python is a programming language."

    @pytest.mark.asyncio
    async def test_includes_built_in_tools_in_request(self, tmp_path):
        executor = OpenAIResponsesExecutor.__new__(OpenAIResponsesExecutor)
        req = _request(labels={"ark.openai.tools/web-search-preview": "true"})

        mock_response = _make_text_response("Search result.")
        captured = {}

        async def mock_create(**kwargs):
            captured.update(kwargs)
            return mock_response

        mock_client = AsyncMock()
        mock_client.responses.create = mock_create

        with patch("openai_responses_executor.executor.SESSIONS_DIR", tmp_path), \
             patch("openai_responses_executor.executor.AsyncOpenAI", return_value=mock_client):
            await executor.execute_agent(req)

        tools = captured.get("tools", [])
        assert {"type": "web_search_preview"} in tools

    @pytest.mark.asyncio
    async def test_error_propagates(self, tmp_path):
        executor = OpenAIResponsesExecutor.__new__(OpenAIResponsesExecutor)
        req = _request()

        mock_client = AsyncMock()
        mock_client.responses.create = AsyncMock(side_effect=RuntimeError("API error"))

        with patch("openai_responses_executor.executor.SESSIONS_DIR", tmp_path), \
             patch("openai_responses_executor.executor.AsyncOpenAI", return_value=mock_client):
            with pytest.raises(RuntimeError, match="API error"):
                await executor.execute_agent(req)
