"""Claude Agent SDK execution logic."""

import logging
import os
from pathlib import Path
from typing import List

from ark_sdk.executor import BaseExecutor, Message
from ark_sdk.executor_app import is_otel_enabled
from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient

logger = logging.getLogger(__name__)

SESSIONS_DIR = Path(os.getenv("SESSIONS_DIR", "/data/sessions"))
DEFAULT_MODEL = "claude-sonnet-4-20250514"

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
        self.model = os.getenv("ANTHROPIC_MODEL", DEFAULT_MODEL)
        logger.info(f"Claude Agent SDK executor initialized with model: {self.model}")

    async def execute_agent(self, request) -> List[Message]:
        """Execute agent using ClaudeSDKClient and return response messages."""
        conversation_id = request.conversationId
        user_input = request.userInput.content

        if not user_input:
            return [Message(role="assistant", content="Error: user input is required", name=request.agent.name)]

        logger.info(f"Executing Claude Agent SDK query for agent {request.agent.name} (conversation: {conversation_id})")

        session_dir = SESSIONS_DIR / conversation_id
        session_dir.mkdir(parents=True, exist_ok=True)

        # SDK stores sessions at ~/.claude/projects/<mangled-cwd>/, not in cwd
        mangled = str(session_dir).replace("/", "-")
        sdk_session_dir = Path.home() / ".claude" / "projects" / mangled
        has_previous_session = sdk_session_dir.exists() and any(sdk_session_dir.iterdir())
        options = ClaudeAgentOptions(
            model=self.model,
            cwd=str(session_dir),
            continue_conversation=has_previous_session,
            permission_mode="bypassPermissions",
        )
        logger.info(f"{'Resuming' if has_previous_session else 'Starting new'} session for conversation {conversation_id}")

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
