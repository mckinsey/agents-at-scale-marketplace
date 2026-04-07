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

    @classmethod
    def from_params(cls, params: dict[str, Any], request: ExecutionEngineRequest) -> "WebSearchTool":
        return cls(
            user_location=WebSearchUserLocation.from_request(request),
            search_context_size=params.get("search_context_size"),
        )


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

    @classmethod
    def from_params(cls, params: dict[str, Any], request: ExecutionEngineRequest) -> "FileSearchTool":
        return cls(
            vector_store_ids=params.get("vector_store_ids"),
            max_num_results=params.get("max_num_results"),
            ranking_options=FileSearchRankingOptions(**params["ranking_options"]) if "ranking_options" in params else None,
        )


# ---------------------------------------------------------------------------
# Code interpreter
# ---------------------------------------------------------------------------


class CodeInterpreterContainer(BaseModel):
    type: Literal["auto"] = "auto"


class CodeInterpreterTool(BaseModel):
    """OpenAI built-in code interpreter tool."""

    type: Literal["code_interpreter"] = "code_interpreter"
    container: Optional[CodeInterpreterContainer] = None

    @classmethod
    def from_params(cls, params: dict[str, Any], request: ExecutionEngineRequest) -> "CodeInterpreterTool":
        return cls(container=CodeInterpreterContainer() if params.get("container") else None)


# ---------------------------------------------------------------------------
# Computer use
# ---------------------------------------------------------------------------


class ComputerUseTool(BaseModel):
    """OpenAI built-in computer use tool."""

    type: Literal["computer_use_preview"] = "computer_use_preview"
    display_width: Optional[int] = None
    display_height: Optional[int] = None

    @classmethod
    def from_params(cls, params: dict[str, Any], request: ExecutionEngineRequest) -> "ComputerUseTool":
        return cls(display_width=params.get("display_width"), display_height=params.get("display_height"))


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
# Built-in tools registry
# ---------------------------------------------------------------------------

# (label, tools_config key, BuiltInTools field name, tool class)
_TOOL_REGISTRY: list[tuple[str, str, str, type]] = [
    (_LABEL_WEB_SEARCH,      "web_search",      "web_search",      WebSearchTool),
    (_LABEL_FILE_SEARCH,     "file_search",      "file_search",     FileSearchTool),
    (_LABEL_CODE_INTERPRETER,"code_interpreter", "code_interpreter",CodeInterpreterTool),
    (_LABEL_COMPUTER_USE,    "computer_use",     "computer_use",    ComputerUseTool),
]


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

        tools: dict[str, Any] = {}
        for label, param_key, field_name, tool_cls in _TOOL_REGISTRY:
            if labels.get(label) == "true":
                tools[field_name] = tool_cls.from_params(tool_params.get(param_key, {}), request)

        return cls(**tools)

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
