"""Claude Agent SDK execution logic."""

import logging
import os
from pathlib import Path
from typing import List

from ark_sdk.executor import BaseExecutor, Message
from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient

logger = logging.getLogger(__name__)

SESSIONS_DIR = Path(os.getenv("SESSIONS_DIR", "/data/sessions"))
DEFAULT_MODEL = "claude-sonnet-4-20250514"


def _init_otel() -> None:
    """Initialize OTEL tracing if OTEL_EXPORTER_OTLP_ENDPOINT is set."""
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    if not endpoint:
        logger.info("OTEL_EXPORTER_OTLP_ENDPOINT not set, tracing disabled")
        return

    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from openinference.instrumentation.claude_agent_sdk import ClaudeAgentSDKInstrumentor

        provider = TracerProvider()
        provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
        trace.set_tracer_provider(provider)
        ClaudeAgentSDKInstrumentor().instrument()
        logger.info(f"OTEL tracing enabled, exporting to {endpoint}")
    except Exception:
        logger.exception("Failed to initialize OTEL tracing")


# Initialize OTEL at module load time
_init_otel()


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

        # Check if a previous session exists to resume
        claude_state_dir = session_dir / ".claude"
        options = ClaudeAgentOptions(
            model=self.model,
            cwd=str(session_dir),
        )
        if claude_state_dir.exists():
            options.resume = True
            logger.info(f"Resuming existing session for conversation {conversation_id}")
        else:
            logger.info(f"Starting new session for conversation {conversation_id}")

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
