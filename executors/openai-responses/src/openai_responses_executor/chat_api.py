"""SSE chat endpoint that pairs with the file UI.

This is a UI-side shortcut: the executor's normal A2A path goes through
Ark (Query CR → A2A → BaseExecutor.execute_agent). For the file-assistant
UI hosted on this pod we cut out the Ark control plane and call OpenAI
directly, reusing:

* ``resolve_agent_context`` for the agent's Model creds + prompt;
* ``file_index`` for the per-agent ``file_ids`` to attach;
* ``previous_response_id`` files on the PVC for conversation threading
  (same path the BaseExecutor uses).

Production traffic should still go via Ark. This endpoint exists so the
upload UI feels like the dashboard chat without requiring the dashboard
or an Ark control plane.
"""

from __future__ import annotations

import json
import logging
from typing import Any, AsyncIterator

from starlette.requests import Request
from starlette.responses import JSONResponse, StreamingResponse
from starlette.routing import Route

from .agent_credentials import (
    AgentContext,
    parse_agent_ref,
    resolve_agent_context,
)
from .config import config
from .file_index import get_index

logger = logging.getLogger(__name__)


def _agent_param(request: Request) -> tuple[str, str] | None:
    raw = request.query_params.get("agent")
    if not raw:
        return None
    return parse_agent_ref(raw)


def _env_context() -> AgentContext:
    if not config.openai_api_key:
        raise ValueError(
            "No API key configured. Either pass ?agent=<name> on the request "
            "or set OPENAI_API_KEY env var on the executor.",
        )
    return AgentContext(
        api_key=config.openai_api_key,
        base_url=config.openai_base_url or None,
        model_name=config.default_chat_model,
        instructions=config.default_chat_instructions,
    )


async def _resolve_context(request: Request) -> AgentContext:
    agent = _agent_param(request)
    if agent is None:
        return _env_context()
    namespace, name = agent
    ctx = await resolve_agent_context(name, namespace)
    if ctx is not None:
        return ctx
    logger.info(
        "agent %s/%s did not resolve; using env fallback for /chat",
        namespace,
        name,
    )
    return _env_context()


def _file_ids_for(request: Request) -> list[str]:
    agent = _agent_param(request)
    if agent is None:
        return []
    _, name = agent
    try:
        return list(get_index(config.sessions_dir).list_for_agent(name))
    except Exception as e:
        logger.warning("file_index list failed for %s: %s", name, e)
        return []


def _conv_dir(conversation_id: str):
    return config.sessions_dir / conversation_id


def _get_previous_response_id(conversation_id: str) -> str | None:
    path = _conv_dir(conversation_id) / "response_id"
    if path.exists():
        return path.read_text().strip() or None
    return None


def _save_response_id(conversation_id: str, response_id: str) -> None:
    d = _conv_dir(conversation_id)
    d.mkdir(parents=True, exist_ok=True)
    (d / "response_id").write_text(response_id)


def _clear_conversation(conversation_id: str) -> None:
    path = _conv_dir(conversation_id) / "response_id"
    if path.exists():
        path.unlink()


def _build_input(
    user_text: str,
    file_ids: list[str],
    previous_response_id: str | None,
) -> str | list[dict[str, Any]]:
    if previous_response_id:
        # Continuation turns can be plain text — the server already has the
        # prior file_ids in its response state. Re-attaching them confuses
        # the model with duplicate input_file parts.
        return user_text
    if not file_ids:
        return user_text
    content: list[dict[str, Any]] = [{"type": "input_file", "file_id": fid} for fid in file_ids]
    content.append({"type": "input_text", "text": user_text})
    return [{"role": "user", "content": content}]


def _sse(event: dict[str, Any]) -> str:
    return f"data: {json.dumps(event)}\n\n"


async def _stream_chat(
    ctx: AgentContext,
    message: str,
    conversation_id: str,
    file_ids: list[str],
) -> AsyncIterator[str]:
    from openai import AsyncOpenAI

    client = AsyncOpenAI(
        api_key=ctx.api_key,
        **({"base_url": ctx.base_url} if ctx.base_url else {}),
    )
    prev_id = _get_previous_response_id(conversation_id)
    api_kwargs: dict[str, Any] = {
        "model": ctx.model_name,
        "instructions": ctx.instructions,
        "input": _build_input(message, file_ids, prev_id),
    }
    if prev_id:
        api_kwargs["previous_response_id"] = prev_id

    yield _sse({
        "type": "start",
        "model": ctx.model_name,
        "file_ids": file_ids if not prev_id else [],
        "conversationId": conversation_id,
    })

    try:
        async with client.responses.stream(**api_kwargs) as stream:
            async for event in stream:
                if event.type == "response.output_text.delta":
                    yield _sse({"type": "delta", "text": event.delta})
            final = await stream.get_final_response()
        _save_response_id(conversation_id, final.id)
        yield _sse({"type": "done", "response_id": final.id})
    except Exception as e:
        logger.exception("chat stream failed")
        yield _sse({"type": "error", "error": str(e)})


async def chat(request: Request) -> StreamingResponse | JSONResponse:
    try:
        body = await request.json()
    except json.JSONDecodeError:
        return JSONResponse({"error": "Body must be JSON"}, status_code=400)

    message = (body.get("message") or "").strip()
    if not message:
        return JSONResponse({"error": "message is required"}, status_code=400)

    conversation_id = (body.get("conversationId") or "").strip()
    if not conversation_id:
        return JSONResponse({"error": "conversationId is required"}, status_code=400)

    try:
        ctx = await _resolve_context(request)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)

    file_ids = _file_ids_for(request)

    return StreamingResponse(
        _stream_chat(ctx, message, conversation_id, file_ids),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


async def reset_chat(request: Request) -> JSONResponse:
    try:
        body = await request.json()
    except json.JSONDecodeError:
        body = {}
    conversation_id = (body.get("conversationId") or "").strip()
    if not conversation_id:
        return JSONResponse({"error": "conversationId is required"}, status_code=400)
    _clear_conversation(conversation_id)
    return JSONResponse({"ok": True, "conversationId": conversation_id})


chat_api_routes = [
    Route("/chat", chat, methods=["POST"]),
    Route("/chat/reset", reset_chat, methods=["POST"]),
]
