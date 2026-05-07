"""OpenAI Responses API executor with file input support."""

import logging
from typing import Any, Optional

from ark_sdk.executor import BaseExecutor, ExecutionEngineRequest, Message
from ark_sdk.executor_app import is_otel_enabled

from .config import config
from .models import ModelConfig, ResponsesCreateParams, resolve_built_in_tools, resolve_reasoning, resolve_output_schema

logger = logging.getLogger(__name__)

if is_otel_enabled():
    try:
        from openinference.instrumentation.openai import OpenAIInstrumentor
        OpenAIInstrumentor().instrument()
        logger.info("OpenAI OTEL instrumentation enabled")
    except Exception:
        logger.exception("Failed to instrument OpenAI")


class OpenAIFileInputsExecutor(BaseExecutor):
    """Executes agents via the OpenAI Responses API with file input support.

    Reads file_ids from the request and builds input_file content parts
    for the Responses API. Supports streaming and conversation threading.
    """

    def __init__(self) -> None:
        super().__init__("OpenAIFileInputs")

    # ------------------------------------------------------------------
    # Session persistence
    # ------------------------------------------------------------------

    @staticmethod
    def _get_previous_response_id(conversation_id: str) -> Optional[str]:
        session_file = config.sessions_dir / conversation_id / "response_id"
        if session_file.exists():
            return session_file.read_text().strip() or None
        return None

    @staticmethod
    def _save_response_id(conversation_id: str, response_id: str) -> None:
        session_dir = config.sessions_dir / conversation_id
        session_dir.mkdir(parents=True, exist_ok=True)
        (session_dir / "response_id").write_text(response_id)

    # ------------------------------------------------------------------
    # Response parsing
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_text_output(response: Any) -> Optional[str]:
        for item in response.output:
            if getattr(item, "type", None) == "message":
                for part in getattr(item, "content", []):
                    if getattr(part, "type", None) == "output_text":
                        return part.text
        return None

    # ------------------------------------------------------------------
    # Main execution
    # ------------------------------------------------------------------

    async def execute_agent(self, request: ExecutionEngineRequest) -> list[Message]:
        conversation_id = getattr(request, "conversationId", None) or request.agent.name
        file_ids = getattr(request.userInput, "file_ids", None) or []

        model_config = ModelConfig.from_request(request)
        instructions = self._resolve_prompt(request.agent)
        tools = resolve_built_in_tools(request) or None
        reasoning = resolve_reasoning(request) if model_config.model_name.startswith("gpt-5") else None
        output_schema = resolve_output_schema(request)
        previous_response_id = self._get_previous_response_id(conversation_id)

        logger.info(
            f"Executing OpenAI Responses API query for agent {request.agent.name} "
            f"(model: {model_config.model_name}, conversation: {conversation_id}, "
            f"files: {len(file_ids)}, "
            f"{'resuming' if previous_response_id else 'new session'})"
        )

        client = model_config.build_client()

        if previous_response_id:
            params = ResponsesCreateParams.continuation(
                model_config=model_config,
                instructions=instructions,
                previous_response_id=previous_response_id,
                input=request.userInput.content,
                tools=tools,
                reasoning=reasoning,
                text=output_schema,
            )
        else:
            params = ResponsesCreateParams.first_turn(
                model_config=model_config,
                instructions=instructions,
                request=request,
                tools=tools,
                reasoning=reasoning,
                text=output_schema,
            )

        try:
            api_kwargs = params.to_api_kwargs()

            response = None
            async with client.responses.stream(**api_kwargs) as stream:
                async for event in stream:
                    if event.type == "response.output_text.delta":
                        await self.stream_chunk(event.delta)
                response = await stream.get_final_response()

            self._save_response_id(conversation_id, response.id)

            text = self._extract_text_output(response) or "No response generated"
            return [Message(role="assistant", content=text, name=request.agent.name)]
        except Exception as e:
            logger.error(f"Error in OpenAI Responses API processing: {e}", exc_info=True)
            raise
