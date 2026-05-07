"""Pydantic models for OpenAI Responses API with file input support."""

import json
import logging
from typing import TYPE_CHECKING, Any, Literal, Optional, Union
from pydantic import BaseModel

from ark_sdk.executor import ExecutionEngineRequest

if TYPE_CHECKING:
    from openai import AsyncAzureOpenAI, AsyncOpenAI

logger = logging.getLogger(__name__)

ANNOTATION_KEY = "executor-openai-file-inputs.ark.mckinsey.com/tools"
REASONING_ANNOTATION_KEY = "executor-openai-file-inputs.ark.mckinsey.com/reasoning"
OUTPUT_SCHEMA_ANNOTATION_KEY = "executor-openai-file-inputs.ark.mckinsey.com/output-schema"


# ---------------------------------------------------------------------------
# Model config
# ---------------------------------------------------------------------------


class AzureModelConfig(BaseModel):
    apiKey: str
    baseUrl: str
    apiVersion: str


class OpenAIModelConfig(BaseModel):
    apiKey: str
    baseUrl: Optional[str] = None


class ModelConfig(BaseModel):
    model_name: str
    api_key: str
    provider: str = "openai"
    base_url: Optional[str] = None
    api_version: Optional[str] = None

    def build_client(self) -> "Union[AsyncOpenAI, AsyncAzureOpenAI]":
        from openai import AsyncAzureOpenAI, AsyncOpenAI
        if self.provider == "azure":
            return AsyncAzureOpenAI(
                api_key=self.api_key,
                azure_endpoint=self.base_url,
                api_version=self.api_version,
            )
        return AsyncOpenAI(
            api_key=self.api_key,
            **({"base_url": self.base_url} if self.base_url else {}),
        )

    @classmethod
    def from_request(cls, request: ExecutionEngineRequest) -> "ModelConfig":
        model = getattr(request.agent, "model", None)
        if model is None:
            raise ValueError("Agent must have a model configured via Model CRD")

        config = getattr(model, "config", None) or {}
        provider = getattr(model, "type", "openai") or "openai"

        if provider == "azure":
            azure = AzureModelConfig.model_validate(config.get("azure") or {})
            return cls(model_name=model.name, api_key=azure.apiKey, provider="azure", base_url=azure.baseUrl, api_version=azure.apiVersion)

        openai = OpenAIModelConfig.model_validate(config.get("openai") or {})
        return cls(model_name=model.name, api_key=openai.apiKey, provider="openai", base_url=openai.baseUrl)


# ---------------------------------------------------------------------------
# Built-in tool resolution via annotations
# ---------------------------------------------------------------------------


def _parse_tools_annotation(value: str) -> list[dict[str, Any]]:
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
    merged: dict[str, dict[str, Any]] = {t["type"]: t for t in base if "type" in t}
    for tool in override:
        if "type" in tool:
            merged[tool["type"]] = tool
        else:
            logger.warning("Skipping tool without 'type' key: %s", tool)
    return list(merged.values())


def resolve_built_in_tools(request: ExecutionEngineRequest) -> list[dict[str, Any]]:
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
# Input building — multimodal with file support
# ---------------------------------------------------------------------------


def _build_content_parts(text: str, file_ids: list[str]) -> list[dict[str, Any]]:
    """Build a multimodal content array with input_file and input_text parts."""
    parts: list[dict[str, Any]] = []
    for fid in file_ids:
        parts.append({"type": "input_file", "file_id": fid})
    parts.append({"type": "input_text", "text": text})
    return parts


def build_user_input(text: str, file_ids: list[str]) -> dict[str, Any]:
    """Build a user message dict, using multimodal content when files are attached."""
    if file_ids:
        return {"role": "user", "content": _build_content_parts(text, file_ids)}
    return {"role": "user", "content": text}


# ---------------------------------------------------------------------------
# Responses API request params
# ---------------------------------------------------------------------------


class ResponsesCreateParams(BaseModel):
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
        file_ids = getattr(request.userInput, "file_ids", None) or []

        input_messages = [
            {"role": msg.role, "content": msg.content} for msg in getattr(request, "history", [])
        ] + [build_user_input(request.userInput.content, file_ids)]

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
