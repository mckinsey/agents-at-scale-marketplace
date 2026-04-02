"""OpenAI Responses API execution logic."""

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ark_sdk.executor import BaseExecutor, ExecutionEngineRequest, Message, ToolDefinition
from openai import AsyncOpenAI

from .models import (
    CodeInterpreterContainer,
    CodeInterpreterTool,
    ComputerUseTool,
    FileSearchRankingOptions,
    FileSearchTool,
    WebSearchTool,
    WebSearchUserLocation,
)

logger = logging.getLogger(__name__)

SESSIONS_DIR = Path(os.getenv("SESSIONS_DIR", "/data/sessions"))

# Maximum tool-call iterations per request to prevent infinite loops
MAX_TOOL_ITERATIONS = 10

# Label keys used to enable OpenAI built-in tools on an Agent CR
_LABEL_WEB_SEARCH = "ark.openai.tools/web-search-preview"
_LABEL_FILE_SEARCH = "ark.openai.tools/file-search"
_LABEL_CODE_INTERPRETER = "ark.openai.tools/code-interpreter"
_LABEL_COMPUTER_USE = "ark.openai.tools/computer-use-preview"


class OpenAIResponsesExecutor(BaseExecutor):
    """Executes agents via the OpenAI Responses API (POST /v1/responses).

    Key differences from the completions executor:
    - Uses ``client.responses.create`` instead of ``client.chat.completions.create``.
    - Conversation threading is handled server-side via ``previous_response_id``
      rather than re-sending the full message history.
    - Supports OpenAI built-in tools (web_search_preview, file_search, etc.)
      alongside custom function tools.
    """

    def __init__(self) -> None:
        super().__init__("OpenAIResponses")

    # ------------------------------------------------------------------
    # Config helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_model_config(request: ExecutionEngineRequest) -> Tuple[str, str, Optional[str]]:
        """Extract model name, API key, and optional base URL from the Model CRD config.

        Returns (model_name, api_key, base_url).
        """
        model = getattr(request.agent, "model", None)
        if model is None:
            raise ValueError("Agent must have a model configured via Model CRD")

        config = getattr(model, "config", None) or {}
        openai_config = config.get("openai")
        if not openai_config:
            raise ValueError(
                "Agent model must have provider 'openai' with apiKey configured via Model CRD"
            )

        api_key = openai_config.get("apiKey")
        if not api_key:
            raise ValueError("Model CRD openai config must include an apiKey")

        model_name = model.name
        base_url = openai_config.get("baseUrl") or None
        return model_name, api_key, base_url

    # ------------------------------------------------------------------
    # Tool helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_function_tools(tools: List[ToolDefinition]) -> List[Dict[str, Any]]:
        """Convert Ark ToolDefinitions to OpenAI Responses API function tool specs."""
        result = []
        for tool in tools:
            parameters = tool.parameters or {"type": "object", "properties": {}}
            result.append(
                {
                    "type": "function",
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": parameters,
                }
            )
        return result

    @staticmethod
    def _get_web_search_user_location(request: ExecutionEngineRequest) -> Optional[WebSearchUserLocation]:
        """Build a ``WebSearchUserLocation`` from Agent CR parameters.

        Reads the following parameter names:
        - ``openai.web-search.country``  (ISO 3166-1 alpha-2, e.g. ``"GB"``)
        - ``openai.web-search.city``
        - ``openai.web-search.region``

        Returns ``None`` if none of the parameters are set.
        """
        params: Dict[str, str] = {
            p.name: p.value for p in (getattr(request.agent, "parameters", None) or [])
        }
        country = params.get("openai.web-search.country")
        city = params.get("openai.web-search.city")
        region = params.get("openai.web-search.region")

        if not any([country, city, region]):
            return None

        return WebSearchUserLocation(country=country, city=city, region=region)

    @staticmethod
    def _get_built_in_tools(request: ExecutionEngineRequest) -> List[Dict[str, Any]]:
        """Return OpenAI built-in tool specs based on Agent CR labels.

        Tool availability (which tools are enabled) is a static, per-agent
        decision controlled via Agent CR labels (value must be ``"true"``):
        - ``ark.openai.tools/web-search-preview``
        - ``ark.openai.tools/file-search``
        - ``ark.openai.tools/code-interpreter``
        - ``ark.openai.tools/computer-use-preview``

        Tool parameters (e.g. vector_store_ids, user_location) are runtime
        config and will be read from the Query CR once ``spec.tools`` is
        supported — for now they fall back to agent parameters where applicable.
        """
        labels: Dict[str, str] = getattr(request.agent, "labels", {}) or {}
        # TODO: read tool params from request.tools_config once Query CR
        # supports spec.tools — currently falling back to agent parameters.
        tool_params: Dict[str, Any] = getattr(request, "tools_config", None) or {}
        built_in = []

        if labels.get(_LABEL_WEB_SEARCH) == "true":
            web_params = tool_params.get("web_search", {})
            user_location = OpenAIResponsesExecutor._get_web_search_user_location(request)
            tool = WebSearchTool(
                user_location=user_location,
                search_context_size=web_params.get("search_context_size"),
            )
            built_in.append(tool.model_dump(exclude_none=True))

        if labels.get(_LABEL_FILE_SEARCH) == "true":
            fs_params = tool_params.get("file_search", {})
            ranking = None
            if "ranking_options" in fs_params:
                ranking = FileSearchRankingOptions(**fs_params["ranking_options"])
            tool_fs = FileSearchTool(
                vector_store_ids=fs_params.get("vector_store_ids"),
                max_num_results=fs_params.get("max_num_results"),
                ranking_options=ranking,
            )
            built_in.append(tool_fs.model_dump(exclude_none=True))

        if labels.get(_LABEL_CODE_INTERPRETER) == "true":
            ci_params = tool_params.get("code_interpreter", {})
            container = None
            if ci_params.get("container"):
                container = CodeInterpreterContainer()
            tool_ci = CodeInterpreterTool(container=container)
            built_in.append(tool_ci.model_dump(exclude_none=True))

        if labels.get(_LABEL_COMPUTER_USE) == "true":
            cu_params = tool_params.get("computer_use", {})
            tool_cu = ComputerUseTool(
                display_width=cu_params.get("display_width"),
                display_height=cu_params.get("display_height"),
            )
            built_in.append(tool_cu.model_dump(exclude_none=True))

        return built_in

    # ------------------------------------------------------------------
    # Multi-turn session helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _get_previous_response_id(conversation_id: str) -> Optional[str]:
        session_file = SESSIONS_DIR / conversation_id / "response_id"
        if session_file.exists():
            return session_file.read_text().strip() or None
        return None

    @staticmethod
    def _save_response_id(conversation_id: str, response_id: str) -> None:
        session_dir = SESSIONS_DIR / conversation_id
        session_dir.mkdir(parents=True, exist_ok=True)
        (session_dir / "response_id").write_text(response_id)

    # ------------------------------------------------------------------
    # Input / output translation
    # ------------------------------------------------------------------

    @staticmethod
    def _build_first_turn_input(request: ExecutionEngineRequest) -> List[Dict[str, Any]]:
        """Build the full input array for the first turn (history + new user message)."""
        items: List[Dict[str, Any]] = []
        for msg in request.history:
            items.append({"role": msg.role, "content": msg.content})
        items.append({"role": "user", "content": request.userInput.content})
        return items

    @staticmethod
    def _extract_text_output(response: Any) -> Optional[str]:
        """Extract the assistant's text from a Responses API response object."""
        for item in response.output:
            if getattr(item, "type", None) == "message":
                for part in getattr(item, "content", []):
                    if getattr(part, "type", None) == "output_text":
                        return part.text
        return None

    @staticmethod
    def _extract_function_calls(response: Any) -> List[Any]:
        """Return all function_call output items from a response."""
        return [item for item in response.output if getattr(item, "type", None) == "function_call"]

    # ------------------------------------------------------------------
    # Main execution
    # ------------------------------------------------------------------

    async def execute_agent(self, request: ExecutionEngineRequest) -> List[Message]:
        """Execute the agent using the OpenAI Responses API and return response messages."""
        conversation_id = getattr(request, "conversationId", None) or request.agent.name

        model_name, api_key, base_url = self._resolve_model_config(request)

        client_kwargs: Dict[str, Any] = {"api_key": api_key}
        if base_url:
            client_kwargs["base_url"] = base_url

        client = AsyncOpenAI(**client_kwargs)

        system_prompt = self._resolve_prompt(request.agent)
        tools = self._build_function_tools(request.tools) + self._get_built_in_tools(request)
        previous_response_id = self._get_previous_response_id(conversation_id)

        logger.info(
            f"Executing OpenAI Responses API query for agent {request.agent.name} "
            f"(model: {model_name}, conversation: {conversation_id}, "
            f"{'resuming' if previous_response_id else 'new session'})"
        )

        # First call: use previous_response_id for multi-turn efficiency, or full history
        if previous_response_id:
            # Server already has the prior conversation; only send the new message
            input_payload: Any = request.userInput.content
        else:
            input_payload = self._build_first_turn_input(request)

        create_kwargs: Dict[str, Any] = {
            "model": model_name,
            "instructions": system_prompt,
            "input": input_payload,
        }
        if tools:
            create_kwargs["tools"] = tools
        if previous_response_id:
            create_kwargs["previous_response_id"] = previous_response_id

        try:
            for iteration in range(MAX_TOOL_ITERATIONS):
                response = await client.responses.create(**create_kwargs)

                # Persist the response ID for the next turn
                self._save_response_id(conversation_id, response.id)

                function_calls = self._extract_function_calls(response)

                if not function_calls:
                    # No pending tool calls — return the text output
                    text = self._extract_text_output(response)
                    if text is None:
                        text = "No response generated"
                    return [Message(role="assistant", content=text, name=request.agent.name)]

                logger.info(
                    f"Iteration {iteration + 1}: executing {len(function_calls)} function call(s) "
                    f"for agent {request.agent.name}"
                )

                # Execute each function call and collect results
                tool_outputs: List[Dict[str, Any]] = []
                for fc in function_calls:
                    result = await self._execute_function_call(fc, request)
                    tool_outputs.append(
                        {
                            "type": "function_call_output",
                            "call_id": fc.call_id,
                            "output": json.dumps(result),
                        }
                    )

                # Continue the conversation with the tool results
                create_kwargs = {
                    "model": model_name,
                    "instructions": system_prompt,
                    "previous_response_id": response.id,
                    "input": tool_outputs,
                }
                if tools:
                    create_kwargs["tools"] = tools

            logger.warning(
                f"Agent {request.agent.name} reached max tool iterations ({MAX_TOOL_ITERATIONS})"
            )
            return [
                Message(
                    role="assistant",
                    content=f"Reached maximum tool call iterations ({MAX_TOOL_ITERATIONS}). "
                    "Please refine your request.",
                    name=request.agent.name,
                )
            ]

        except Exception as e:
            logger.error(f"Error in OpenAI Responses API processing: {e}", exc_info=True)
            raise

    # ------------------------------------------------------------------
    # Function tool execution
    # ------------------------------------------------------------------

    async def _execute_function_call(self, function_call: Any, request: ExecutionEngineRequest) -> Any:
        """Execute a custom function tool call.

        Attempts to find the tool's HTTP endpoint from the agent's tool definitions
        and call it. Falls back to a structured error if the tool is not resolvable.
        """
        tool_name = function_call.name
        try:
            arguments = json.loads(function_call.arguments) if function_call.arguments else {}
        except json.JSONDecodeError:
            arguments = {"raw": function_call.arguments}

        # Look up the tool in the request's tool definitions
        matching = [t for t in request.tools if t.name == tool_name]
        if not matching:
            logger.warning(f"Function tool '{tool_name}' not found in agent tool definitions")
            return {"error": f"Tool '{tool_name}' is not available for this agent"}

        logger.info(f"Executing function tool '{tool_name}' with arguments: {arguments}")

        # Tool HTTP execution requires the tool endpoint URL which is provided via
        # Ark's internal tool infrastructure (not yet exposed in ExecutionEngineRequest).
        # This will be wired up as the Ark SDK evolves.
        logger.warning(
            f"HTTP execution of tool '{tool_name}' is not yet implemented in this executor. "
            "Returning placeholder result."
        )
        return {"error": f"Tool '{tool_name}' HTTP execution not yet implemented", "arguments": arguments}
