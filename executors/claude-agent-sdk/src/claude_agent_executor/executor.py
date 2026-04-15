"""Claude Agent SDK execution logic."""

import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from ark_sdk.executor import BaseExecutor, MCPServerConfig, Message
from ark_sdk.executor_app import is_otel_enabled
from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient, list_sessions

logger = logging.getLogger(__name__)

SESSIONS_DIR = Path(os.getenv("SESSIONS_DIR", "/data/sessions"))

# Executor-specific instrumentation — only the Claude Agent SDK instrumentor
if is_otel_enabled():
    try:
        from openinference.instrumentation.claude_agent_sdk import ClaudeAgentSDKInstrumentor
        ClaudeAgentSDKInstrumentor().instrument()
        logger.info("Claude Agent SDK OTEL instrumentation enabled")
    except Exception:
        logger.exception("Failed to instrument Claude Agent SDK")


class ClaudeAgentExecutor(BaseExecutor):
    """Handles Claude Agent SDK execution with built-in tool access."""

    def __init__(self) -> None:
        super().__init__("ClaudeAgentSDK")
        logger.info("Claude Agent SDK executor initialized")

    @staticmethod
    def _resolve_model_config(request) -> Tuple[str, str, Optional[str]]:
        """Extract model name, API key, and optional base URL from the Model CRD config.

        Returns (model_name, api_key, base_url).
        """
        model = getattr(request.agent, "model", None)
        if model is None:
            raise ValueError(
                "Agent model must have provider 'anthropic' with apiKey configured via Model CRD"
            )

        config = getattr(model, "config", None) or {}
        anthropic_config = config.get("anthropic")
        if not anthropic_config:
            raise ValueError(
                "Agent model must have provider 'anthropic' with apiKey configured via Model CRD"
            )

        api_key = anthropic_config.get("apiKey")
        if not api_key:
            raise ValueError(
                "Model CRD anthropic config must include an apiKey"
            )

        model_name = model.name
        base_url = anthropic_config.get("baseUrl") or None

        return model_name, api_key, base_url

    @staticmethod
    def _build_mcp_options(mcp_servers: List[MCPServerConfig]) -> Tuple[Dict, List[str]]:
        """Map Ark MCPServerConfig list to Claude SDK mcp_servers dict and allowed_tools list."""
        sdk_servers: Dict[str, dict] = {}
        allowed_tools: List[str] = []

        for server in mcp_servers:
            if not server.tools:
                continue
            sdk_servers[server.name] = {
                "type": server.transport,
                "url": server.url,
                "headers": server.headers,
            }
            for tool_name in server.tools:
                allowed_tools.append(f"mcp__{server.name}__{tool_name}")

        return sdk_servers, allowed_tools

    async def execute_agent(self, request) -> List[Message]:
        """Execute agent using ClaudeSDKClient and return response messages."""
        conversation_id = request.conversationId
        user_input = request.userInput.content

        if not user_input:
            return [Message(role="assistant", content="Error: user input is required", name=request.agent.name)]

        model_name, api_key, base_url = self._resolve_model_config(request)

        logger.info(f"Executing Claude Agent SDK query for agent {request.agent.name} (model: {model_name}, conversation: {conversation_id})")

        session_dir = SESSIONS_DIR / conversation_id
        session_dir.mkdir(parents=True, exist_ok=True)

        # Find existing session to resume
        previous_session_id = None
        try:
            sessions = list_sessions(directory=str(session_dir), limit=1)
            if sessions:
                previous_session_id = sessions[0].session_id
        except Exception:
            logger.debug("Could not list sessions for %s", session_dir, exc_info=True)

        mcp_kwargs: Dict = {}
        mcp_servers = getattr(request, "mcpServers", None) or []
        if mcp_servers:
            sdk_servers, allowed_tools = self._build_mcp_options(mcp_servers)
            if sdk_servers:
                mcp_kwargs["mcp_servers"] = sdk_servers
                mcp_kwargs["allowed_tools"] = allowed_tools
                summary = ", ".join(f"{s.name} ({len(s.tools)} tools)" for s in mcp_servers if s.tools)
                logger.info(f"Connecting {len(sdk_servers)} MCP servers: {summary}")

        env: Dict[str, str] = dict(os.environ)
        env["ANTHROPIC_API_KEY"] = api_key
        if base_url:
            env["ANTHROPIC_BASE_URL"] = base_url

        resume_kwargs: Dict = {}
        if previous_session_id:
            resume_kwargs["resume"] = previous_session_id
        options = ClaudeAgentOptions(
            model=model_name,
            cwd=str(session_dir),
            permission_mode="bypassPermissions",
            env=env,
            **mcp_kwargs,
            **resume_kwargs,
        )
        logger.info(f"{'Resuming session ' + previous_session_id if previous_session_id else 'Starting new session'} for conversation {conversation_id}")

        try:
            result_text = ""
            async with ClaudeSDKClient(options=options) as client:
                await client.query(user_input)
                async for message in client.receive_response():
                    if hasattr(message, "result") and message.result:
                        result_text = message.result

            if not result_text:
                result_text = "No response generated"

            return [Message(role="assistant", content=result_text, name=request.agent.name)]

        except Exception as e:
            logger.error(f"Error in Claude Agent SDK processing: {e}", exc_info=True)
            raise
