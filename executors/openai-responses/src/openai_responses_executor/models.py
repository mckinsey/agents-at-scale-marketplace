"""Pydantic models for OpenAI Responses API tool declarations and request building."""

from typing import Any, Literal, Optional, Union
from pydantic import BaseModel

from ark_sdk.executor import ExecutionEngineRequest, ToolDefinition


# ---------------------------------------------------------------------------
# Label keys for built-in tool enablement on Agent CR
# ---------------------------------------------------------------------------

_LABEL_WEB_SEARCH = "ark.openai.tools/web-search-preview"
_LABEL_FILE_SEARCH = "ark.openai.tools/file-search"
_LABEL_CODE_INTERPRETER = "ark.openai.tools/code-interpreter"
_LABEL_COMPUTER_USE = "ark.openai.tools/computer-use-preview"


# ---------------------------------------------------------------------------
# Model config
# ---------------------------------------------------------------------------


class ModelConfig(BaseModel):
    """OpenAI credentials and model name extracted from the Model CRD."""

    model_name: str
    api_key: str
    base_url: Optional[str] = None

    @classmethod
    def from_request(cls, request: ExecutionEngineRequest) -> "ModelConfig":
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

        return cls(
            model_name=model.name,
            api_key=api_key,
            base_url=openai_config.get("baseUrl") or None,
        )


# ---------------------------------------------------------------------------
# Web search
# ---------------------------------------------------------------------------


class WebSearchUserLocation(BaseModel):
    """Approximate location hint passed to the web_search_preview tool."""

    type: Literal["approximate"] = "approximate"
    country: Optional[str] = None
    city: Optional[str] = None
    region: Optional[str] = None

    @classmethod
    def from_request(cls, request: ExecutionEngineRequest) -> Optional["WebSearchUserLocation"]:
        params: dict[str, str] = {
            p.name: p.value for p in (getattr(request.agent, "parameters", None) or [])
        }
        country = params.get("openai.web-search.country")
        city = params.get("openai.web-search.city")
        region = params.get("openai.web-search.region")

        if not any([country, city, region]):
            return None
        return cls(country=country, city=city, region=region)


class WebSearchTool(BaseModel):
    """OpenAI built-in web search tool."""

    type: Literal["web_search_preview"] = "web_search_preview"
    user_location: Optional[WebSearchUserLocation] = None
    search_context_size: Optional[Literal["low", "medium", "high"]] = None


# ---------------------------------------------------------------------------
# File search
# ---------------------------------------------------------------------------


class FileSearchRankingOptions(BaseModel):
    ranker: Optional[Literal["auto", "default_2024_08_21"]] = None
    score_threshold: Optional[float] = None


class FileSearchTool(BaseModel):
    """OpenAI built-in file search tool.

    ``vector_store_ids`` are runtime parameters — they should come from the
    Query CR (spec.tools.file_search.vector_store_ids) rather than being
    hardcoded on the Agent CR.
    """

    type: Literal["file_search"] = "file_search"
    vector_store_ids: Optional[list[str]] = None
    max_num_results: Optional[int] = None
    ranking_options: Optional[FileSearchRankingOptions] = None


# ---------------------------------------------------------------------------
# Code interpreter
# ---------------------------------------------------------------------------


class CodeInterpreterContainer(BaseModel):
    type: Literal["auto"] = "auto"


class CodeInterpreterTool(BaseModel):
    """OpenAI built-in code interpreter tool."""

    type: Literal["code_interpreter"] = "code_interpreter"
    container: Optional[CodeInterpreterContainer] = None


# ---------------------------------------------------------------------------
# Computer use
# ---------------------------------------------------------------------------


class ComputerUseTool(BaseModel):
    """OpenAI built-in computer use tool."""

    type: Literal["computer_use_preview"] = "computer_use_preview"
    display_width: Optional[int] = None
    display_height: Optional[int] = None


# ---------------------------------------------------------------------------
# Function tool
# ---------------------------------------------------------------------------


class FunctionTool(BaseModel):
    """Custom function tool derived from an Ark ToolDefinition."""

    type: Literal["function"] = "function"
    name: str
    description: str
    parameters: dict[str, Any] = {"type": "object", "properties": {}}

    @classmethod
    def from_definition(cls, tool: ToolDefinition) -> "FunctionTool":
        return cls(
            name=tool.name,
            description=tool.description,
            parameters=tool.parameters or {"type": "object", "properties": {}},
        )


# ---------------------------------------------------------------------------
# Built-in tools collection
# ---------------------------------------------------------------------------


class BuiltInTools(BaseModel):
    """All OpenAI built-in tools enabled for an agent, built from the Ark request."""

    web_search: Optional[WebSearchTool] = None
    file_search: Optional[FileSearchTool] = None
    code_interpreter: Optional[CodeInterpreterTool] = None
    computer_use: Optional[ComputerUseTool] = None

    @classmethod
    def from_request(cls, request: ExecutionEngineRequest) -> "BuiltInTools":
        labels: dict[str, str] = getattr(request.agent, "labels", {}) or {}
        # TODO: read from request.tools_config once Query CR supports spec.tools
        tool_params: dict[str, Any] = getattr(request, "tools_config", None) or {}

        web_search = None
        if labels.get(_LABEL_WEB_SEARCH) == "true":
            ws = tool_params.get("web_search", {})
            web_search = WebSearchTool(
                user_location=WebSearchUserLocation.from_request(request),
                search_context_size=ws.get("search_context_size"),
            )

        file_search = None
        if labels.get(_LABEL_FILE_SEARCH) == "true":
            fs = tool_params.get("file_search", {})
            file_search = FileSearchTool(
                vector_store_ids=fs.get("vector_store_ids"),
                max_num_results=fs.get("max_num_results"),
                ranking_options=FileSearchRankingOptions(**fs["ranking_options"]) if "ranking_options" in fs else None,
            )

        code_interpreter = None
        if labels.get(_LABEL_CODE_INTERPRETER) == "true":
            ci = tool_params.get("code_interpreter", {})
            code_interpreter = CodeInterpreterTool(
                container=CodeInterpreterContainer() if ci.get("container") else None,
            )

        computer_use = None
        if labels.get(_LABEL_COMPUTER_USE) == "true":
            cu = tool_params.get("computer_use", {})
            computer_use = ComputerUseTool(
                display_width=cu.get("display_width"),
                display_height=cu.get("display_height"),
            )

        return cls(
            web_search=web_search,
            file_search=file_search,
            code_interpreter=code_interpreter,
            computer_use=computer_use,
        )

    def to_list(self) -> list[dict[str, Any]]:
        return [
            tool.model_dump(exclude_none=True)
            for tool in [self.web_search, self.file_search, self.code_interpreter, self.computer_use]
            if tool is not None
        ]


# ---------------------------------------------------------------------------
# Responses API request params
# ---------------------------------------------------------------------------


class ResponsesCreateParams(BaseModel):
    """Full parameters for a client.responses.create() call."""

    model: str
    instructions: str
    input: Union[str, list[dict[str, Any]]]
    tools: Optional[list[dict[str, Any]]] = None
    previous_response_id: Optional[str] = None

    def to_api_kwargs(self) -> dict[str, Any]:
        return self.model_dump(exclude_none=True)

    @classmethod
    def first_turn(
        cls,
        model_config: ModelConfig,
        instructions: str,
        request: ExecutionEngineRequest,
        tools: Optional[list[dict[str, Any]]],
    ) -> "ResponsesCreateParams":
        input_messages = [
            {"role": msg.role, "content": msg.content} for msg in request.history
        ] + [{"role": "user", "content": request.userInput.content}]

        return cls(
            model=model_config.model_name,
            instructions=instructions,
            input=input_messages,
            tools=tools or None,
        )

    @classmethod
    def continuation(
        cls,
        model_config: ModelConfig,
        instructions: str,
        previous_response_id: str,
        input: Union[str, list[dict[str, Any]]],
        tools: Optional[list[dict[str, Any]]],
    ) -> "ResponsesCreateParams":
        return cls(
            model=model_config.model_name,
            instructions=instructions,
            input=input,
            tools=tools or None,
            previous_response_id=previous_response_id,
        )
