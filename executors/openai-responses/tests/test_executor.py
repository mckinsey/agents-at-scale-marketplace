"""Unit tests for OpenAI Responses API executor."""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from ark_sdk.executor import Message, ToolDefinition
from openai_responses_executor.executor import OpenAIResponsesExecutor
from openai_responses_executor.models import (
    BuiltInTools,
    FunctionTool,
    ModelConfig,
    ResponsesCreateParams,
    WebSearchUserLocation,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _model_config(name="gpt-4o", api_key="sk-test-key", base_url=None):
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


def _param(name, value):
    p = MagicMock()
    p.name = name
    p.value = value
    return p


def _request(
    agent_name="test-agent",
    model=None,
    labels=None,
    tools=None,
    history=None,
    conversation_id="conv-123",
    user_content="hello",
    parameters=None,
):
    req = MagicMock()
    req.agent.name = agent_name
    req.agent.model = model or _model_config()
    req.agent.labels = labels or {}
    req.agent.prompt = "You are a helpful assistant."
    req.agent.parameters = parameters or []
    req.tools = tools or []
    req.history = history or []
    req.userInput.content = user_content
    req.conversationId = conversation_id
    req.tools_config = None
    return req


# ---------------------------------------------------------------------------
# ModelConfig
# ---------------------------------------------------------------------------


class TestModelConfig:
    def test_valid_openai_config(self):
        req = _request(model=_model_config("gpt-4o", "sk-abc", "https://proxy.example.com"))
        mc = ModelConfig.from_request(req)

        assert mc.model_name == "gpt-4o"
        assert mc.api_key == "sk-abc"
        assert mc.base_url == "https://proxy.example.com"

    def test_no_base_url(self):
        req = _request(model=_model_config("gpt-4o", "sk-abc"))
        mc = ModelConfig.from_request(req)

        assert mc.model_name == "gpt-4o"
        assert mc.base_url is None

    def test_missing_openai_config_raises(self):
        req = _request()
        req.agent.model.config = {"anthropic": {"apiKey": "sk-ant"}}
        with pytest.raises(ValueError, match="provider 'openai'"):
            ModelConfig.from_request(req)

    def test_missing_api_key_raises(self):
        req = _request()
        req.agent.model.config = {"openai": {"baseUrl": "https://proxy.example.com"}}
        with pytest.raises(ValueError, match="apiKey"):
            ModelConfig.from_request(req)

    def test_no_model_raises(self):
        req = _request()
        req.agent.model = None
        with pytest.raises(ValueError, match="model"):
            ModelConfig.from_request(req)


# ---------------------------------------------------------------------------
# FunctionTool
# ---------------------------------------------------------------------------


class TestFunctionTool:
    def test_from_definition(self):
        tool = FunctionTool.from_definition(_tool("search", "Search the web"))
        result = tool.model_dump()

        assert result["type"] == "function"
        assert result["name"] == "search"
        assert result["description"] == "Search the web"
        assert "parameters" in result

    def test_empty_parameters_gets_defaults(self):
        tool = FunctionTool.from_definition(ToolDefinition(name="ping", description="Ping", parameters={}))
        assert tool.parameters == {"type": "object", "properties": {}}


# ---------------------------------------------------------------------------
# WebSearchUserLocation
# ---------------------------------------------------------------------------


class TestWebSearchUserLocation:
    def test_full_location(self):
        req = _request(parameters=[
            _param("openai.web-search.country", "GB"),
            _param("openai.web-search.city", "London"),
            _param("openai.web-search.region", "London"),
        ])
        result = WebSearchUserLocation.from_request(req)

        assert isinstance(result, WebSearchUserLocation)
        assert result.country == "GB"
        assert result.city == "London"
        assert result.region == "London"

    def test_country_only(self):
        req = _request(parameters=[_param("openai.web-search.country", "US")])
        result = WebSearchUserLocation.from_request(req)

        assert result.country == "US"
        assert result.city is None

    def test_no_params_returns_none(self):
        result = WebSearchUserLocation.from_request(_request())
        assert result is None


# ---------------------------------------------------------------------------
# BuiltInTools
# ---------------------------------------------------------------------------


class TestBuiltInTools:
    def test_web_search_enabled(self):
        req = _request(labels={"ark.openai.tools/web-search-preview": "true"})
        result = BuiltInTools.from_request(req).to_list()
        assert {"type": "web_search_preview"} in result

    def test_web_search_with_user_location(self):
        req = _request(
            labels={"ark.openai.tools/web-search-preview": "true"},
            parameters=[_param("openai.web-search.country", "GB")],
        )
        result = BuiltInTools.from_request(req).to_list()

        assert result[0]["type"] == "web_search_preview"
        assert result[0]["user_location"] == {"type": "approximate", "country": "GB"}

    def test_multiple_tools(self):
        req = _request(labels={
            "ark.openai.tools/web-search-preview": "true",
            "ark.openai.tools/code-interpreter": "true",
        })
        types = [t["type"] for t in BuiltInTools.from_request(req).to_list()]
        assert "web_search_preview" in types
        assert "code_interpreter" in types

    def test_no_labels_returns_empty(self):
        assert BuiltInTools.from_request(_request()).to_list() == []

    def test_label_false_not_included(self):
        req = _request(labels={"ark.openai.tools/web-search-preview": "false"})
        assert BuiltInTools.from_request(req).to_list() == []

    def test_file_search_and_computer_use(self):
        req = _request(labels={
            "ark.openai.tools/file-search": "true",
            "ark.openai.tools/computer-use-preview": "true",
        })
        types = [t["type"] for t in BuiltInTools.from_request(req).to_list()]
        assert "file_search" in types
        assert "computer_use_preview" in types


# ---------------------------------------------------------------------------
# ResponsesCreateParams
# ---------------------------------------------------------------------------


class TestResponsesCreateParams:
    def _model_config_obj(self):
        return ModelConfig(model_name="gpt-4o", api_key="sk-test")

    def test_first_turn_no_history(self):
        req = _request(user_content="what is 2+2?")
        params = ResponsesCreateParams.first_turn(self._model_config_obj(), "You are helpful.", req, None)

        assert params.input == [{"role": "user", "content": "what is 2+2?"}]
        assert params.previous_response_id is None

    def test_first_turn_with_history(self):
        history = [Message(role="user", content="hi"), Message(role="assistant", content="hello")]
        req = _request(history=history, user_content="what is 2+2?")
        params = ResponsesCreateParams.first_turn(self._model_config_obj(), "You are helpful.", req, None)

        assert len(params.input) == 3
        assert params.input[-1] == {"role": "user", "content": "what is 2+2?"}

    def test_continuation(self):
        params = ResponsesCreateParams.continuation(
            self._model_config_obj(), "instructions", "resp-prev", "follow-up", None
        )
        assert params.previous_response_id == "resp-prev"
        assert params.input == "follow-up"

    def test_to_api_kwargs_excludes_none(self):
        params = ResponsesCreateParams.first_turn(self._model_config_obj(), "instructions", _request(), None)
        kwargs = params.to_api_kwargs()
        assert "previous_response_id" not in kwargs
        assert "tools" not in kwargs


# ---------------------------------------------------------------------------
# Session helpers
# ---------------------------------------------------------------------------


class TestSessionHelpers:
    def test_save_and_get_response_id(self, tmp_path):
        with patch("openai_responses_executor.executor.config") as mock_cfg:
            mock_cfg.sessions_dir = tmp_path
            OpenAIResponsesExecutor._save_response_id("conv-1", "resp-abc123")
            result = OpenAIResponsesExecutor._get_previous_response_id("conv-1")
        assert result == "resp-abc123"

    def test_get_response_id_missing_returns_none(self, tmp_path):
        with patch("openai_responses_executor.executor.config") as mock_cfg:
            mock_cfg.sessions_dir = tmp_path
            result = OpenAIResponsesExecutor._get_previous_response_id("conv-nonexistent")
        assert result is None


# ---------------------------------------------------------------------------
# execute_agent
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
    def _mock_config(self, tmp_path):
        mock_cfg = MagicMock()
        mock_cfg.sessions_dir = tmp_path
        mock_cfg.max_tool_iterations = 10
        return mock_cfg

    @pytest.mark.asyncio
    async def test_simple_text_response(self, tmp_path):
        executor = OpenAIResponsesExecutor.__new__(OpenAIResponsesExecutor)
        req = _request()
        mock_response = _make_text_response("Paris is the capital of France.")
        mock_client = AsyncMock()
        mock_client.responses.create = AsyncMock(return_value=mock_response)

        with patch("openai_responses_executor.executor.config", self._mock_config(tmp_path)), \
             patch("openai_responses_executor.executor.AsyncOpenAI", return_value=mock_client):
            messages = await executor.execute_agent(req)

        assert messages[0].content == "Paris is the capital of France."
        assert messages[0].role == "assistant"

    @pytest.mark.asyncio
    async def test_uses_previous_response_id_on_second_turn(self, tmp_path):
        executor = OpenAIResponsesExecutor.__new__(OpenAIResponsesExecutor)
        req = _request()

        session_dir = tmp_path / "conv-123"
        session_dir.mkdir()
        (session_dir / "response_id").write_text("resp-prev-001")

        mock_response = _make_text_response("Follow-up answer.")
        captured = {}

        async def capture_create(**kwargs):
            captured.update(kwargs)
            return mock_response

        mock_client = AsyncMock()
        mock_client.responses.create = capture_create

        with patch("openai_responses_executor.executor.config", self._mock_config(tmp_path)), \
             patch("openai_responses_executor.executor.AsyncOpenAI", return_value=mock_client):
            await executor.execute_agent(req)

        assert captured.get("previous_response_id") == "resp-prev-001"
        assert captured.get("input") == "hello"

    @pytest.mark.asyncio
    async def test_saves_response_id_after_call(self, tmp_path):
        executor = OpenAIResponsesExecutor.__new__(OpenAIResponsesExecutor)
        req = _request()
        mock_response = _make_text_response("Answer.", response_id="resp-saved-001")
        mock_client = AsyncMock()
        mock_client.responses.create = AsyncMock(return_value=mock_response)

        with patch("openai_responses_executor.executor.config", self._mock_config(tmp_path)), \
             patch("openai_responses_executor.executor.AsyncOpenAI", return_value=mock_client):
            await executor.execute_agent(req)

        assert (tmp_path / "conv-123" / "response_id").read_text() == "resp-saved-001"

    @pytest.mark.asyncio
    async def test_function_call_loop(self, tmp_path):
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

        with patch("openai_responses_executor.executor.config", self._mock_config(tmp_path)), \
             patch("openai_responses_executor.executor.AsyncOpenAI", return_value=mock_client):
            messages = await executor.execute_agent(req)

        assert call_count == 2
        assert messages[0].content == "Python is a programming language."

    @pytest.mark.asyncio
    async def test_includes_built_in_tools_in_request(self, tmp_path):
        executor = OpenAIResponsesExecutor.__new__(OpenAIResponsesExecutor)
        req = _request(labels={"ark.openai.tools/web-search-preview": "true"})
        captured = {}

        async def mock_create(**kwargs):
            captured.update(kwargs)
            return _make_text_response("Result.")

        mock_client = AsyncMock()
        mock_client.responses.create = mock_create

        with patch("openai_responses_executor.executor.config", self._mock_config(tmp_path)), \
             patch("openai_responses_executor.executor.AsyncOpenAI", return_value=mock_client):
            await executor.execute_agent(req)

        assert {"type": "web_search_preview"} in captured.get("tools", [])

    @pytest.mark.asyncio
    async def test_error_propagates(self, tmp_path):
        executor = OpenAIResponsesExecutor.__new__(OpenAIResponsesExecutor)
        req = _request()
        mock_client = AsyncMock()
        mock_client.responses.create = AsyncMock(side_effect=RuntimeError("API error"))

        with patch("openai_responses_executor.executor.config", self._mock_config(tmp_path)), \
             patch("openai_responses_executor.executor.AsyncOpenAI", return_value=mock_client):
            with pytest.raises(RuntimeError, match="API error"):
                await executor.execute_agent(req)
