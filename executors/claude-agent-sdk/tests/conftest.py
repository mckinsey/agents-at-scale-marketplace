"""Stub out claude_agent_sdk for local test runs (the real package is Docker/Linux-only)."""

import sys
import types
from dataclasses import dataclass, field
from typing import Any, Optional


def _build_stub() -> None:
    if "claude_agent_sdk" in sys.modules:
        return

    @dataclass
    class TextBlock:
        text: str

    @dataclass
    class ThinkingBlock:
        thinking: str
        signature: str

    @dataclass
    class ToolUseBlock:
        id: str
        name: str
        input: dict = field(default_factory=dict)

    @dataclass
    class ToolResultBlock:
        tool_use_id: str
        content: str

    @dataclass
    class AssistantMessage:
        content: list
        model: str
        parent_tool_use_id: Optional[str] = None
        error: Optional[str] = None

    @dataclass
    class ResultMessage:
        subtype: str = "success"
        duration_ms: int = 0
        duration_api_ms: int = 0
        is_error: bool = False
        num_turns: int = 0
        session_id: str = ""
        total_cost_usd: Optional[float] = None
        usage: Optional[dict] = None
        result: Optional[str] = None
        structured_output: Any = None

    @dataclass
    class ClaudeAgentOptions:
        model: str = ""
        cwd: str = "."
        permission_mode: str = "default"
        env: dict = field(default_factory=dict)
        mcp_servers: Optional[dict] = None
        allowed_tools: Optional[list] = None
        resume: Optional[str] = None

    class ClaudeSDKClient:
        def __init__(self, options=None):
            self.options = options

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def query(self, prompt):
            pass

        async def receive_response(self):
            return
            yield

    def list_sessions(directory=".", limit=10):
        return []

    sdk_types = types.ModuleType("claude_agent_sdk.types")
    sdk_types.TextBlock = TextBlock
    sdk_types.ThinkingBlock = ThinkingBlock
    sdk_types.ToolUseBlock = ToolUseBlock
    sdk_types.ToolResultBlock = ToolResultBlock
    sdk_types.AssistantMessage = AssistantMessage
    sdk_types.ResultMessage = ResultMessage
    sdk_types.ClaudeAgentOptions = ClaudeAgentOptions

    sdk = types.ModuleType("claude_agent_sdk")
    sdk.ClaudeAgentOptions = ClaudeAgentOptions
    sdk.ClaudeSDKClient = ClaudeSDKClient
    sdk.list_sessions = list_sessions
    sdk.types = sdk_types

    sys.modules["claude_agent_sdk"] = sdk
    sys.modules["claude_agent_sdk.types"] = sdk_types


_build_stub()
