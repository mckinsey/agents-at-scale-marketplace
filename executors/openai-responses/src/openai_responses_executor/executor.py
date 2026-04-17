"""OpenAI Responses API execution logic."""

import json
import logging
import os
from typing import Any, Optional

from ark_sdk.executor import BaseExecutor, ExecutionEngineRequest, Message
from openai import AsyncOpenAI, AsyncAzureOpenAI

from .config import config
from .models import FunctionTool, ModelConfig, ResponsesCreateParams, resolve_built_in_tools, resolve_reasoning, resolve_output_schema

logger = logging.getLogger(__name__)

if os.getenv("OTEL_INSTRUMENTATION_ENABLED", "false").lower() == "true":
    try:
        from openinference.instrumentation.openai import OpenAIInstrumentor
        OpenAIInstrumentor().instrument()
        logger.info("OpenAI OTEL instrumentation enabled")
    except Exception:
        logger.exception("Failed to instrument OpenAI")
        raise


class OpenAIResponsesExecutor(BaseExecutor):
    """Executes agents via the OpenAI Responses API (POST /v1/responses).

    - Conversation threading via ``previous_response_id`` (no full history resend).
    - Built-in tools (web_search_preview, file_search, code_interpreter, computer_use).
    - Custom function tool call loop.
    """

    def __init__(self) -> None:
        super().__init__("OpenAIResponses")

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
            # CFG custom tool calls return constrained output in `input` field
            if getattr(item, "type", None) == "custom_tool_call":
                return getattr(item, "input", None)
        return None

    @staticmethod
    def _extract_function_calls(response: Any) -> list[Any]:
        return [item for item in response.output if getattr(item, "type", None) == "function_call"]

    # ------------------------------------------------------------------
    # Main execution
    # ------------------------------------------------------------------

    async def execute_agent(self, request: ExecutionEngineRequest) -> list[Message]:
        conversation_id = getattr(request, "conversationId", None) or request.agent.name

        model_config = ModelConfig.from_request(request)
        instructions = self._resolve_prompt(request.agent)
        tools = (
            [FunctionTool.from_definition(t).model_dump() for t in getattr(request, "tools", [])]
            + resolve_built_in_tools(request)
        )
        # reasoning only supported on gpt-5+; temperature not supported on gpt-5+
        reasoning = resolve_reasoning(request) if model_config.model_name.startswith("gpt-5") else None
        output_schema = resolve_output_schema(request)
        previous_response_id = self._get_previous_response_id(conversation_id)

        logger.info(
            f"Executing OpenAI Responses API query for agent {request.agent.name} "
            f"(model: {model_config.model_name}, conversation: {conversation_id}, "
            f"{'resuming' if previous_response_id else 'new session'})"
        )

        if model_config.provider == "azure":
            if not model_config.base_url:
                raise ValueError("Model CRD azure config must include a baseUrl")
            if not model_config.api_version:
                raise ValueError("Model CRD azure config must include an apiVersion")
            client = AsyncAzureOpenAI(
                api_key=model_config.api_key,
                azure_endpoint=model_config.base_url,
                api_version=model_config.api_version,
            )
        else:
            client = AsyncOpenAI(
                api_key=model_config.api_key,
                **({"base_url": model_config.base_url} if model_config.base_url else {}),
            )

        if previous_response_id:
            params = ResponsesCreateParams.continuation(
                model_config=model_config,
                instructions=instructions,
                previous_response_id=previous_response_id,
                input=request.userInput.content,
                tools=tools or None,
                reasoning=reasoning,
                text=output_schema,
            )
        else:
            params = ResponsesCreateParams.first_turn(
                model_config=model_config,
                instructions=instructions,
                request=request,
                tools=tools or None,
                reasoning=reasoning,
                text=output_schema,
            )

        try:
            return await self._run_tool_loop(client, params, model_config, instructions, tools, request, conversation_id)
        except Exception as e:
            logger.error(f"Error in OpenAI Responses API processing: {e}", exc_info=True)
            raise

    async def _run_tool_loop(
        self,
        client: Any,
        params: ResponsesCreateParams,
        model_config: Any,
        instructions: str,
        tools: list[Any],
        request: ExecutionEngineRequest,
        conversation_id: str,
    ) -> list[Message]:
        for iteration in range(config.max_tool_iterations):
            api_kwargs = params.to_api_kwargs()
            logger.info(f"Request tools: {api_kwargs.get('tools')}")

            response = None
            async with client.responses.stream(**api_kwargs) as stream:
                async for event in stream:
                    if event.type == "response.output_text.delta":
                        await self.stream_chunk(event.delta)
                response = await stream.get_final_response()

            self._save_response_id(conversation_id, response.id)
            logger.info(f"Response output types: {[getattr(item, 'type', None) for item in response.output]}")

            function_calls = self._extract_function_calls(response)

            if not function_calls:
                text = self._extract_text_output(response) or "No response generated"
                return [Message(role="assistant", content=text, name=request.agent.name)]

            logger.info(
                f"Iteration {iteration + 1}: executing {len(function_calls)} function call(s) "
                f"for agent {request.agent.name}"
            )

            tool_outputs = [
                {
                    "type": "function_call_output",
                    "call_id": fc.call_id,
                    "output": json.dumps(await self._execute_function_call(fc, request)),
                }
                for fc in function_calls
            ]

            params = ResponsesCreateParams.continuation(
                model_config=model_config,
                instructions=instructions,
                previous_response_id=response.id,
                input=tool_outputs,
                tools=tools or None,
            )

        logger.warning(f"Agent {request.agent.name} reached max tool iterations ({config.max_tool_iterations})")
        return [
            Message(
                role="assistant",
                content=f"Reached maximum tool call iterations ({config.max_tool_iterations}). Please refine your request.",
                name=request.agent.name,
            )
        ]

    # ------------------------------------------------------------------
    # Function tool execution
    # ------------------------------------------------------------------

    async def _execute_function_call(self, function_call: Any, request: ExecutionEngineRequest) -> Any:
        tool_name = function_call.name
        try:
            arguments = json.loads(function_call.arguments) if function_call.arguments else {}
        except json.JSONDecodeError:
            arguments = {"raw": function_call.arguments}

        if not any(getattr(t, "name", t) == tool_name for t in getattr(request, "tools", [])):
            logger.warning(f"Function tool '{tool_name}' not found in agent tool definitions")
            return {"error": f"Tool '{tool_name}' is not available for this agent"}

        logger.info(f"Executing function tool '{tool_name}' with arguments: {arguments}")

        # Tool HTTP execution requires the tool endpoint URL from Ark's tool infrastructure.
        # This will be wired up as the Ark SDK evolves.
        logger.warning(f"HTTP execution of tool '{tool_name}' is not yet implemented.")
        return {"error": f"Tool '{tool_name}' HTTP execution not yet implemented", "arguments": arguments}
