"""Pydantic models for OpenAI Responses API tool declarations and request building."""

import json
import logging
from typing import Any, Literal, Optional, Union
from pydantic import BaseModel

from ark_sdk.executor import ExecutionEngineRequest

logger = logging.getLogger(__name__)

# Annotation key for tool configuration on Agent, Query, and ExecutionEngine CRs
ANNOTATION_KEY = "executor-openai-responses.ark.mckinsey.com/tools"
REASONING_ANNOTATION_KEY = "executor-openai-responses.ark.mckinsey.com/reasoning"
OUTPUT_SCHEMA_ANNOTATION_KEY = "executor-openai-responses.ark.mckinsey.com/output-schema"


# ---------------------------------------------------------------------------
# Model config
# ---------------------------------------------------------------------------


class ModelConfig(BaseModel):
    """OpenAI credentials and model name extracted from the Model CRD."""

    model_name: str
    api_key: str
    provider: str = "openai"
    base_url: Optional[str] = None
    api_version: Optional[str] = None

    @classmethod
    def from_request(cls, request: ExecutionEngineRequest) -> "ModelConfig":
        model = getattr(request.agent, "model", None)
        if model is None:
            raise ValueError("Agent must have a model configured via Model CRD")

        config = getattr(model, "config", None) or {}
        provider = getattr(model, "type", "openai") or "openai"

        if provider == "azure":
            azure_config = config.get("azure") or {}
            api_key = azure_config.get("apiKey")
            if not api_key:
                raise ValueError("Model CRD azure config must include an apiKey")
            return cls(
                model_name=model.name,
                api_key=api_key,
                provider="azure",
                base_url=azure_config.get("baseUrl") or None,
                api_version=azure_config.get("apiVersion") or None,
            )

        openai_config = config.get("openai")
        if not openai_config:
            raise ValueError(
                "Agent model must have provider 'openai' or 'azure' with apiKey configured via Model CRD"
            )
        api_key = openai_config.get("apiKey")
        if not api_key:
            raise ValueError("Model CRD openai config must include an apiKey")
        return cls(
            model_name=model.name,
            api_key=api_key,
            provider="openai",
            base_url=openai_config.get("baseUrl") or None,
        )


# ---------------------------------------------------------------------------
# Built-in tool resolution via annotations
# ---------------------------------------------------------------------------


def _parse_tools_annotation(value: str) -> list[dict[str, Any]]:
    """Parse a JSON tool array from an annotation value. Returns [] on failure."""
    if not value:
        return []
    try:
        tools = json.loads(value)
        if not isinstance(tools, list):
            logger.warning("Tools annotation must be a JSON array, got %s", type(tools).__name__)
            return []
        return tools
    except json.JSONDecodeError as exc:
        logger.warning("Failed to parse tools annotation: %s", exc)
        return []


def _merge_tools(base: list[dict[str, Any]], override: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Merge two tool arrays, replacing entries with matching 'type' keys."""
    merged: dict[str, dict[str, Any]] = {t["type"]: t for t in base if "type" in t}
    for tool in override:
        if "type" in tool:
            merged[tool["type"]] = tool
        else:
            logger.warning("Skipping tool without 'type' key: %s", tool)
    return list(merged.values())


def resolve_built_in_tools(request: ExecutionEngineRequest) -> list[dict[str, Any]]:
    """Resolve built-in tools using the annotation cascade.

    Cascade order (lowest → highest priority):
        ExecutionEngine annotations → Agent annotations → Query annotations

    Each layer merges by 'type' key: same type replaces, new type is added.
    """
    engine_tools = _parse_tools_annotation(
        request.execution_engine_annotations.get(ANNOTATION_KEY, "")
    )
    agent_tools = _parse_tools_annotation(
        (getattr(request.agent, "annotations", None) or {}).get(ANNOTATION_KEY, "")
    )
    query_tools = _parse_tools_annotation(
        request.query_annotations.get(ANNOTATION_KEY, "")
    )

    tools = _merge_tools(engine_tools, agent_tools)
    tools = _merge_tools(tools, query_tools)
    return tools


def resolve_reasoning(request: ExecutionEngineRequest) -> Optional[dict[str, Any]]:
    """Resolve reasoning config from annotations (Agent overrides ExecutionEngine, Query overrides Agent)."""
    for source in [
        request.execution_engine_annotations,
        (getattr(request.agent, "annotations", None) or {}),
        request.query_annotations,
    ]:
        raw = source.get(REASONING_ANNOTATION_KEY, "")
        if raw:
            try:
                return json.loads(raw)
            except json.JSONDecodeError as exc:
                logger.warning("Failed to parse reasoning annotation: %s", exc)
    return None


def resolve_output_schema(request: ExecutionEngineRequest) -> Optional[dict[str, Any]]:
    """Resolve JSON output schema from annotations. Returns text.format dict or None."""
    for source in [
        request.execution_engine_annotations,
        (getattr(request.agent, "annotations", None) or {}),
        request.query_annotations,
    ]:
        raw = source.get(OUTPUT_SCHEMA_ANNOTATION_KEY, "")
        if raw:
            try:
                schema = json.loads(raw)
                return {"format": {"type": "json_schema", "name": "output", "schema": schema}}
            except json.JSONDecodeError as exc:
                logger.warning("Failed to parse output-schema annotation: %s", exc)
    return None


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
    def from_definition(cls, tool: Any) -> "FunctionTool":
        return cls(
            name=tool.name,
            description=getattr(tool, "description", ""),
            parameters=getattr(tool, "parameters", None) or {"type": "object", "properties": {}},
        )


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
    reasoning: Optional[dict[str, Any]] = None
    text: Optional[dict[str, Any]] = None

    def to_api_kwargs(self) -> dict[str, Any]:
        return self.model_dump(exclude_none=True)

    @classmethod
    def first_turn(
        cls,
        model_config: ModelConfig,
        instructions: str,
        request: ExecutionEngineRequest,
        tools: Optional[list[dict[str, Any]]],
        reasoning: Optional[dict[str, Any]] = None,
        text: Optional[dict[str, Any]] = None,
    ) -> "ResponsesCreateParams":
        input_messages = [
            {"role": msg.role, "content": msg.content} for msg in getattr(request, "history", [])
        ] + [{"role": "user", "content": request.userInput.content}]

        return cls(
            model=model_config.model_name,
            instructions=instructions,
            input=input_messages,
            tools=tools or None,
            reasoning=reasoning,
            text=text,
        )

    @classmethod
    def continuation(
        cls,
        model_config: ModelConfig,
        instructions: str,
        previous_response_id: str,
        input: Union[str, list[dict[str, Any]]],
        tools: Optional[list[dict[str, Any]]],
        reasoning: Optional[dict[str, Any]] = None,
        text: Optional[dict[str, Any]] = None,
    ) -> "ResponsesCreateParams":
        return cls(
            model=model_config.model_name,
            instructions=instructions,
            input=input,
            tools=tools or None,
            previous_response_id=previous_response_id,
            reasoning=reasoning,
            text=text,
        )
