"""Tests for MCP server option mapping and Model CRD config in ClaudeAgentExecutor."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from ark_sdk.executor import MCPServerConfig, Message
from claude_agent_executor.executor import ClaudeAgentExecutor


def _server(name="srv", url="http://srv:8080", transport="http", headers=None, tools=None):
    return MCPServerConfig(
        name=name,
        url=url,
        transport=transport,
        headers=headers or {},
        tools=tools or [],
    )


def _model_config(name="claude-sonnet-4-20250514", api_key="sk-test-key", base_url=None):
    """Build a mock model object matching Model CRD structure."""
    anthropic = {"apiKey": api_key}
    if base_url is not None:
        anthropic["baseUrl"] = base_url
    model = MagicMock()
    model.name = name
    model.config = {"anthropic": anthropic}
    return model


class TestBuildMcpOptions:
    def test_single_server(self):
        servers = [_server(name="github-mcp", url="http://github:8080", transport="http",
                           headers={"Authorization": "Bearer tok"}, tools=["search_repos", "create_issue"])]

        sdk_servers, allowed_tools = ClaudeAgentExecutor._build_mcp_options(servers)

        assert sdk_servers == {
            "github-mcp": {
                "type": "http",
                "url": "http://github:8080",
                "headers": {"Authorization": "Bearer tok"},
            }
        }
        assert allowed_tools == ["mcp__github-mcp__search_repos", "mcp__github-mcp__create_issue"]

    def test_multiple_servers(self):
        servers = [
            _server(name="github-mcp", url="http://github:8080", tools=["search_repos"]),
            _server(name="slack-mcp", url="http://slack:8080/sse", transport="sse", tools=["send_message", "list_channels"]),
        ]

        sdk_servers, allowed_tools = ClaudeAgentExecutor._build_mcp_options(servers)

        assert len(sdk_servers) == 2
        assert "github-mcp" in sdk_servers
        assert "slack-mcp" in sdk_servers
        assert sdk_servers["slack-mcp"]["type"] == "sse"
        assert set(allowed_tools) == {
            "mcp__github-mcp__search_repos",
            "mcp__slack-mcp__send_message",
            "mcp__slack-mcp__list_channels",
        }

    def test_empty_servers_list(self):
        sdk_servers, allowed_tools = ClaudeAgentExecutor._build_mcp_options([])

        assert sdk_servers == {}
        assert allowed_tools == []

    def test_server_with_empty_tools_skipped(self):
        servers = [
            _server(name="empty-srv", tools=[]),
            _server(name="real-srv", tools=["do_thing"]),
        ]

        sdk_servers, allowed_tools = ClaudeAgentExecutor._build_mcp_options(servers)

        assert "empty-srv" not in sdk_servers
        assert "real-srv" in sdk_servers
        assert allowed_tools == ["mcp__real-srv__do_thing"]


class TestResolveModelConfig:
    def test_valid_anthropic_config(self):
        request = MagicMock()
        request.agent.model = _model_config(
            name="claude-opus-4-20250514",
            api_key="sk-ant-abc123",
            base_url="https://proxy.internal.example.com",
        )

        model_name, api_key, base_url = ClaudeAgentExecutor._resolve_model_config(request)

        assert model_name == "claude-opus-4-20250514"
        assert api_key == "sk-ant-abc123"
        assert base_url == "https://proxy.internal.example.com"

    def test_missing_anthropic_config(self):
        request = MagicMock()
        request.agent.model = MagicMock()
        request.agent.model.config = {"openai": {"apiKey": "sk-openai"}}

        with pytest.raises(ValueError, match="provider 'anthropic'"):
            ClaudeAgentExecutor._resolve_model_config(request)

    def test_missing_api_key(self):
        request = MagicMock()
        request.agent.model = MagicMock()
        request.agent.model.name = "claude-sonnet-4-20250514"
        request.agent.model.config = {"anthropic": {"baseUrl": "https://proxy.example.com"}}

        with pytest.raises(ValueError, match="must include an apiKey"):
            ClaudeAgentExecutor._resolve_model_config(request)

    def test_no_base_url(self):
        request = MagicMock()
        request.agent.model = _model_config(
            name="claude-sonnet-4-20250514",
            api_key="sk-ant-xyz789",
        )

        model_name, api_key, base_url = ClaudeAgentExecutor._resolve_model_config(request)

        assert model_name == "claude-sonnet-4-20250514"
        assert api_key == "sk-ant-xyz789"
        assert base_url is None


class TestExecuteAgentMcpIntegration:
    @pytest.mark.asyncio
    async def test_mcp_servers_passed_to_options(self, tmp_path):
        executor = ClaudeAgentExecutor.__new__(ClaudeAgentExecutor)

        request = MagicMock()
        request.conversationId = "test-conv"
        request.userInput.content = "hello"
        request.agent.name = "test-agent"
        request.agent.model = _model_config()
        request.mcpServers = [
            _server(name="github-mcp", url="http://github:8080", headers={"Auth": "Bearer x"}, tools=["search"]),
        ]

        captured_options = {}

        class FakeClient:
            def __init__(self, options=None):
                captured_options["options"] = options

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

            async def query(self, prompt):
                pass

            async def receive_response(self):
                msg = MagicMock()
                msg.result = "done"
                yield msg

        with patch("claude_agent_executor.executor.SESSIONS_DIR", tmp_path), \
             patch("claude_agent_executor.executor.ClaudeSDKClient", FakeClient):
            await executor.execute_agent(request)

        opts = captured_options["options"]
        assert opts.mcp_servers == {"github-mcp": {"type": "http", "url": "http://github:8080", "headers": {"Auth": "Bearer x"}}}
        assert "mcp__github-mcp__search" in opts.allowed_tools

    @pytest.mark.asyncio
    async def test_no_mcp_servers_no_extra_options(self, tmp_path):
        executor = ClaudeAgentExecutor.__new__(ClaudeAgentExecutor)

        request = MagicMock()
        request.conversationId = "test-conv-2"
        request.userInput.content = "hello"
        request.agent.name = "test-agent"
        request.agent.model = _model_config()
        request.mcpServers = []

        captured_options = {}

        class FakeClient:
            def __init__(self, options=None):
                captured_options["options"] = options

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

            async def query(self, prompt):
                pass

            async def receive_response(self):
                msg = MagicMock()
                msg.result = "done"
                yield msg

        with patch("claude_agent_executor.executor.SESSIONS_DIR", tmp_path), \
             patch("claude_agent_executor.executor.ClaudeSDKClient", FakeClient):
            await executor.execute_agent(request)

        opts = captured_options["options"]
        assert not hasattr(opts, "mcp_servers") or opts.mcp_servers is None
        assert not hasattr(opts, "allowed_tools") or opts.allowed_tools is None
