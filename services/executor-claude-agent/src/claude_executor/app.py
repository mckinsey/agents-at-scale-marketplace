"""FastAPI application for Claude Agent SDK Executor.

Exposes the /execute endpoint required by ARK's ExecutionEngine interface.
"""

import os
import logging
from typing import Annotated, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing_extensions import Doc

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from .executor import ClaudeAgentExecutor, Message

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# ============================================================================
# Pydantic Models for ARK ExecutionEngine Protocol
# ============================================================================


class ExecutionEngineModel(BaseModel):
    """Model configuration from ARK."""
    name: Annotated[str, Doc("Claude model identifier")] = "claude-sonnet-4-20250514"
    type: Annotated[str | None, Doc("Provider type: anthropic or bedrock")] = "anthropic"
    config: Annotated[dict[str, Any] | None, Doc("Additional model configuration")] = None


class AgentConfig(BaseModel):
    """Agent configuration from ARK."""
    name: Annotated[str, Doc("Unique agent identifier")]
    namespace: Annotated[str, Doc("Kubernetes namespace")] = "default"
    prompt: Annotated[str | None, Doc("System prompt for the agent")] = ""
    description: Annotated[str | None, Doc("Human-readable agent description")] = ""
    parameters: Annotated[list[dict[str, Any]] | None, Doc("Agent parameters")] = None
    model: Annotated[ExecutionEngineModel | None, Doc("Model configuration")] = None
    outputSchema: Annotated[dict[str, Any] | None, Doc("JSON schema for structured output")] = None


class MessageInput(BaseModel):
    """Message format from ARK."""
    role: Annotated[str, Doc("Message role: user, assistant, or system")]
    content: Annotated[str, Doc("Message content")]
    name: Annotated[str | None, Doc("Optional sender name")] = None
    tool_calls: Annotated[list[dict[str, Any]] | None, Doc("Tool calls made by assistant")] = None
    tool_call_id: Annotated[str | None, Doc("ID of tool call this message responds to")] = None


class ToolDefinition(BaseModel):
    """Tool definition from ARK."""
    name: Annotated[str, Doc("Tool name")]
    description: Annotated[str | None, Doc("Tool description")] = None
    parameters: Annotated[dict[str, Any] | None, Doc("JSON schema for tool parameters")] = None


class ExecutionEngineRequest(BaseModel):
    """Request format for ARK ExecutionEngine."""
    agent: Annotated[AgentConfig, Doc("Agent configuration")]
    userInput: Annotated[MessageInput, Doc("Current user message")]
    history: Annotated[list[MessageInput], Doc("Conversation history")] = []
    tools: Annotated[list[ToolDefinition], Doc("Available tools")] = []


class MessageOutput(BaseModel):
    """Message output format for ARK."""
    role: Annotated[str, Doc("Message role")]
    content: Annotated[str, Doc("Message content")]
    name: Annotated[str | None, Doc("Agent name")] = None
    tool_calls: Annotated[list[dict[str, Any]] | None, Doc("Tool calls")] = None
    tool_call_id: Annotated[str | None, Doc("Tool call ID")] = None


class TokenUsage(BaseModel):
    """Token usage metrics."""
    inputTokens: Annotated[int, Doc("Input tokens consumed")] = 0
    outputTokens: Annotated[int, Doc("Output tokens generated")] = 0


class ExecutionEngineResponse(BaseModel):
    """Response format for ARK ExecutionEngine."""
    messages: Annotated[list[MessageOutput], Doc("Response messages")]
    error: Annotated[str | None, Doc("Error message if execution failed")] = None
    tokenUsage: Annotated[TokenUsage | None, Doc("Token usage statistics")] = None


# ============================================================================
# OpenTelemetry Setup
# ============================================================================


def init_otel():
    """Initialize OpenTelemetry if configured."""
    otel_endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")
    if not otel_endpoint:
        logger.info("OTEL not configured, skipping initialization")
        return

    otel_protocol = os.environ.get("OTEL_EXPORTER_OTLP_PROTOCOL", "grpc")
    service_name = os.environ.get("OTEL_SERVICE_NAME", "executor-claude")

    logger.info(f"Initializing OTEL: {otel_protocol}@{otel_endpoint}")

    tracer_provider = TracerProvider(
        resource=Resource({"service.name": service_name})
    )

    if otel_protocol == "http/protobuf":
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    else:
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

    span_exporter = OTLPSpanExporter(endpoint=otel_endpoint)
    tracer_provider.add_span_processor(BatchSpanProcessor(span_exporter))
    trace.set_tracer_provider(tracer_provider)

    logger.info(f"OpenTelemetry initialized: {service_name}")


# ============================================================================
# FastAPI Application
# ============================================================================

# Global executor instance
executor: ClaudeAgentExecutor | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    global executor

    # Startup
    logger.info("Starting Claude Agent SDK Executor...")
    init_otel()
    executor = ClaudeAgentExecutor()
    logger.info("Executor initialized successfully")

    yield

    # Shutdown
    logger.info("Shutting down executor...")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Claude Agent SDK Executor",
        description="ARK ExecutionEngine implementation using Claude Agent SDK",
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Instrument with OpenTelemetry
    FastAPIInstrumentor.instrument_app(app)

    @app.get("/health")
    async def health():
        """Health check endpoint."""
        return {"status": "healthy", "executor": "claude"}

    @app.get("/ready")
    async def ready():
        """Readiness check endpoint."""
        if executor is None:
            raise HTTPException(status_code=503, detail="Executor not initialized")
        return {"status": "ready", "executor": "claude"}

    @app.post("/execute", response_model=ExecutionEngineResponse)
    async def execute(request: ExecutionEngineRequest) -> ExecutionEngineResponse:
        """
        Execute an agent request using Claude Agent SDK.

        This is the main endpoint called by ARK's ExecutionEngine client.
        """
        if executor is None:
            raise HTTPException(status_code=503, detail="Executor not initialized")

        logger.info(
            f"Executing agent '{request.agent.name}' with "
            f"{len(request.tools)} tools, {len(request.history)} history messages"
        )

        try:
            # Convert request to dict for executor
            request_dict = {
                "agent": request.agent.model_dump(),
                "userInput": request.userInput.model_dump(),
                "history": [msg.model_dump() for msg in request.history],
                "tools": [tool.model_dump() for tool in request.tools],
            }

            # Execute with Claude Agent SDK
            messages = await executor.execute_agent(request_dict)

            # Convert Message objects to response format
            response_messages = [
                MessageOutput(
                    role=msg.role,
                    content=msg.content,
                    name=msg.name,
                    tool_calls=msg.tool_calls,
                    tool_call_id=msg.tool_call_id,
                )
                for msg in messages
            ]

            return ExecutionEngineResponse(
                messages=response_messages,
                tokenUsage=TokenUsage(inputTokens=0, outputTokens=0),
            )

        except Exception as e:
            logger.error(f"Execution failed: {e}")
            return ExecutionEngineResponse(
                messages=[
                    MessageOutput(
                        role="assistant",
                        content=f"Execution error: {str(e)}",
                        name=request.agent.name,
                    )
                ],
                error=str(e),
            )

    @app.get("/info")
    async def info():
        """Get executor information."""
        return {
            "name": "Claude Agent SDK Executor",
            "type": "claude",
            "version": "0.1.0",
            "capabilities": [
                "agentic_execution",
                "tool_use",
                "multi_turn",
                "file_operations",
                "code_execution",
            ],
            "default_model": os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514"),
            "max_turns": int(os.getenv("CLAUDE_MAX_TURNS", "10")),
        }

    return app


# Create the app instance
app = create_app()


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8000"))
    host = os.getenv("HOST", "0.0.0.0")

    logger.info(f"Starting server on {host}:{port}")
    uvicorn.run(app, host=host, port=port)
