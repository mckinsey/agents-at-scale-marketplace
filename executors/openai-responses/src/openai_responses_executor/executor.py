"""OpenAI Responses API execution logic."""

import json
import logging
import os
from typing import Any, Optional

from ark_sdk.executor import BaseExecutor, ExecutionEngineRequest, Message

from . import sessions
from .config import config
from .mcp_tools import bindable_dict, call_mcp_tool, clean_input_text, discover_mcp_function_tools, render_args
from .models import FunctionTool, ModelConfig, ResponsesCreateParams, resolve_built_in_tools, resolve_reasoning, resolve_file_ids, resolve_output_schema, resolve_max_tool_calls, resolve_mcp_prefetch

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
        # No conversationId = unthreaded query. Don't fall back to agent.name:
        # that would collapse every unthreaded query against an agent into one
        # shared session, leaking previous_response_id state across users.
        conversation_id = getattr(request, "conversationId", None) or None

        model_config = ModelConfig.from_request(request)
        instructions = self._resolve_prompt(request.agent)
        # MCP tools resolved by the ARK SDK (Agent.spec.tools[type:mcp] ->
        # request.mcpServers) are surfaced to the model as OpenAI `function`
        # tools; `mcp_registry` maps each synthesized function name back to its
        # (server, tool) for dispatch and for the prefetch chain.
        mcp_function_tools, mcp_registry = await discover_mcp_function_tools(
            getattr(request, "mcpServers", None) or []
        )

        def _is_mcp_tool(t: Any) -> bool:
            return str(getattr(t, "type", "") or "").lower() == "mcp"

        tools = (
            [FunctionTool.from_definition(t).model_dump() for t in getattr(request, "tools", []) if not _is_mcp_tool(t)]
            + mcp_function_tools
            + resolve_built_in_tools(request)
        )

        # Deterministic prefetch chain (opt-in): run a chain of MCP tool calls up
        # front, inject the results, and answer in a single no-tool turn — trading
        # the model's tool-loop flexibility for fewer model round-trips. Each step
        # may bind its result for later steps' arg templating ({<bind>.<field>}).
        prefetch_steps = resolve_mcp_prefetch(request)
        if prefetch_steps:
            subs: dict[str, str] = {"input": clean_input_text(request.userInput.content)}
            injected: list[str] = []
            ran_any = False
            for step in prefetch_steps:
                entry = mcp_registry.get(step.get("tool"))
                if entry is None:
                    logger.warning("prefetch: tool %s not available; skipping step", step.get("tool"))
                    continue
                server, real_tool = entry
                args = render_args(step.get("args") or {}, subs)
                logger.info("prefetch step: %s args=%s", real_tool, args)
                result = await call_mcp_tool(server, real_tool, args)
                ran_any = True
                bind = step.get("bind")
                if bind:
                    for k, v in bindable_dict(result).items():
                        if isinstance(v, (str, int, float)):
                            subs[f"{bind}.{k}"] = str(v)
                if step.get("inject", True):
                    label = step.get("label") or bind or real_tool
                    injected.append(f"[{label}]:\n{json.dumps(result)[:8000]}")
            if ran_any:
                request.userInput.content = f"{request.userInput.content}\n\n" + "\n\n".join(injected)
                tools = []          # single-turn: no tools exposed to the model
                mcp_registry = {}   # nothing left to dispatch
        # reasoning only supported on gpt-5+; temperature not supported on gpt-5+
        reasoning = resolve_reasoning(request) if model_config.model_name.startswith("gpt-5") else None
        output_schema = resolve_output_schema(request)
        max_tool_calls = resolve_max_tool_calls(request)
        previous_response_id = (
            await sessions.get_previous_response_id(conversation_id) if conversation_id else None
        )

        logger.info(
            f"Executing OpenAI Responses API query for agent {request.agent.name} "
            f"(model: {model_config.model_name}, conversation: {conversation_id or 'unthreaded'}, "
            f"{'resuming' if previous_response_id else 'new session'})"
        )

        client = model_config.build_client()

        file_ids = resolve_file_ids(request)
        if previous_response_id:
            # Attach only files new to this conversation: the threaded response
            # state already holds previously attached files, and Agent-level
            # annotations re-present the same IDs on every turn.
            sent = await sessions.get_sent_file_ids(conversation_id)
            new_file_ids = [fid for fid in file_ids if fid not in sent]
            params = ResponsesCreateParams.continuation(
                model_config=model_config,
                instructions=instructions,
                previous_response_id=previous_response_id,
                input=(
                    [ResponsesCreateParams._build_user_message(request.userInput.content, new_file_ids)]
                    if new_file_ids
                    else request.userInput.content
                ),
                tools=tools or None,
                reasoning=reasoning,
                text=output_schema,
                max_tool_calls=max_tool_calls,
            )
        else:
            params = ResponsesCreateParams.first_turn(
                model_config=model_config,
                instructions=instructions,
                request=request,
                tools=tools or None,
                reasoning=reasoning,
                text=output_schema,
                max_tool_calls=max_tool_calls,
            )

        try:
            result = await self._run_tool_loop(client, params, model_config, instructions, tools, request, conversation_id, mcp_registry)
            if conversation_id and file_ids:
                await sessions.mark_file_ids_sent(conversation_id, set(file_ids))
            return result
        except Exception as e:
            if conversation_id and sessions.is_zdr_threading_error(e):
                await sessions.clear_conversation(conversation_id)
                raise RuntimeError(f"{sessions.ZDR_HINT} (provider error: {e})") from e
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
        conversation_id: Optional[str],
        mcp_registry: Optional[dict[str, Any]] = None,
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

            if conversation_id:
                await sessions.save_response_id(conversation_id, response.id)
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
                    "output": json.dumps(await self._execute_function_call(fc, request, mcp_registry)),
                }
                for fc in function_calls
            ]

            params = ResponsesCreateParams.continuation(
                model_config=model_config,
                instructions=instructions,
                previous_response_id=response.id,
                input=tool_outputs,
                tools=tools or None,
                max_tool_calls=params.max_tool_calls,
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

    async def _execute_function_call(
        self,
        function_call: Any,
        request: ExecutionEngineRequest,
        mcp_registry: Optional[dict[str, Any]] = None,
    ) -> Any:
        tool_name = function_call.name
        try:
            arguments = json.loads(function_call.arguments) if function_call.arguments else {}
        except json.JSONDecodeError:
            arguments = {"raw": function_call.arguments}

        # MCP-backed tools: dispatch tools/call to the resolved MCP server.
        entry = (mcp_registry or {}).get(tool_name)
        if entry is not None:
            server, mcp_tool_name = entry
            logger.info(f"Executing MCP tool '{mcp_tool_name}' (via '{tool_name}') args: {arguments}")
            return await call_mcp_tool(server, mcp_tool_name, arguments)

        if not any(getattr(t, "name", t) == tool_name for t in getattr(request, "tools", [])):
            logger.warning(f"Function tool '{tool_name}' not found in agent tool definitions")
            return {"error": f"Tool '{tool_name}' is not available for this agent"}

        logger.info(f"Executing function tool '{tool_name}' with arguments: {arguments}")

        # Non-MCP ark ToolDefinition HTTP execution is still unimplemented.
        logger.warning(f"HTTP execution of tool '{tool_name}' is not yet implemented.")
        return {"error": f"Tool '{tool_name}' HTTP execution not yet implemented", "arguments": arguments}
