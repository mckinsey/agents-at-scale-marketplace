"""SSE chat endpoint that pairs with the file UI.

This is a UI-side shortcut: the executor's normal A2A path goes through
Ark (Query CR → A2A → BaseExecutor.execute_agent). For the file-assistant
UI hosted on this pod we cut out the Ark control plane and call OpenAI
directly, reusing:

* ``resolve_agent_context`` for the agent's Model creds + prompt;
* ``file_index`` for the per-agent ``file_ids`` to attach;
* the shared ``sessions`` store for conversation threading (same path the
  BaseExecutor uses).

Production traffic should still go via Ark. This endpoint exists so the
upload UI feels like the dashboard chat without requiring the dashboard
or an Ark control plane.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, AsyncIterator

from starlette.requests import Request
from starlette.responses import JSONResponse, StreamingResponse
from starlette.routing import Route

from . import sessions
from .agent_credentials import (
    AgentContext,
    parse_agent_ref,
    resolve_agent_context,
)
from .config import config
from .file_index import ENV_INDEX_KEY, get_index
from .providers import client_for

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
    # Resolution failures (not found, RBAC, bad Secret ref) raise ValueError
    # with the precise reason; an explicit ?agent= must never silently fall
    # back to the env key (wrong OpenAI project).
    ctx = await resolve_agent_context(name, namespace)
    if ctx is None:
        raise ValueError(
            f"Agent {namespace}/{name} has no OpenAI model configured "
            "(no modelRef, or its Model has no openai config). "
            "Drop ?agent= to use the env-var fallback.",
        )
    return ctx


async def _file_ids_for(request: Request) -> list[str]:
    agent = _agent_param(request)
    name = agent[1] if agent is not None else ENV_INDEX_KEY
    try:
        index = get_index(config.sessions_dir)
        return list(await asyncio.to_thread(index.list_for_agent, name))
    except Exception as e:
        logger.warning("file_index list failed for %s: %s", name, e)
        return []


def _build_input(
    user_text: str,
    file_ids: list[str],
) -> str | list[dict[str, Any]]:
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
    client = client_for(ctx.api_key, ctx.base_url)
    prev_id = await sessions.get_previous_response_id(conversation_id)
    # Attach only files new to this conversation: the threaded response state
    # already holds previously attached files, and re-attaching duplicates
    # input_file parts. Files uploaded mid-conversation still attach.
    sent = await sessions.get_sent_file_ids(conversation_id) if prev_id else set()
    attach_ids = [fid for fid in file_ids if fid not in sent]
    api_kwargs: dict[str, Any] = {
        "model": ctx.model_name,
        "instructions": ctx.instructions,
        "input": _build_input(message, attach_ids),
    }
    if prev_id:
        api_kwargs["previous_response_id"] = prev_id

    yield _sse({
        "type": "start",
        "model": ctx.model_name,
        "file_ids": attach_ids,
        "conversationId": conversation_id,
    })

    try:
        async with client.responses.stream(**api_kwargs) as stream:
            async for event in stream:
                if event.type == "response.output_text.delta":
                    yield _sse({"type": "delta", "text": event.delta})
            final = await stream.get_final_response()
        await sessions.save_response_id(conversation_id, final.id)
        await sessions.mark_file_ids_sent(conversation_id, set(attach_ids))
        yield _sse({"type": "done", "response_id": final.id})
    except Exception as e:
        logger.exception("chat stream failed")
        if sessions.is_zdr_threading_error(e):
            await sessions.clear_conversation(conversation_id)
            yield _sse({"type": "error", "error": f"{sessions.ZDR_HINT} (provider error: {e})"})
        else:
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
        sessions.validate_conversation_id(conversation_id)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)

    try:
        ctx = await _resolve_context(request)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)

    # Explicit selection from the UI wins; falling back to "everything in the
    # per-agent index" keeps plain API callers working.
    selected = body.get("file_ids")
    if isinstance(selected, list):
        file_ids = [fid for fid in selected if isinstance(fid, str) and fid]
    else:
        file_ids = await _file_ids_for(request)

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
    try:
        sessions.validate_conversation_id(conversation_id)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    await sessions.clear_conversation(conversation_id)
    return JSONResponse({"ok": True, "conversationId": conversation_id})


chat_api_routes = [
    Route("/chat", chat, methods=["POST"]),
    Route("/chat/reset", reset_chat, methods=["POST"]),
]
