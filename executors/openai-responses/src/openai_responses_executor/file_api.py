"""Provider-agnostic Files API + responses executor UI.

Exposes:
    GET  /                   → responses executor UI (HTML)
    POST /v1/files           → upload (multipart: file, purpose)
    GET  /v1/files           → list
    GET  /v1/files/{file_id} → metadata
    DELETE /v1/files/{file_id}

All endpoints accept ``?agent=<namespace>/<name>`` (or ``<name>``). When set,
credentials are resolved from the agent's Model CR so uploads land in the same
OpenAI project the agent's Responses calls will use; an agent that fails to
resolve is a 400, not a silent fallback. Uploads/deletes are recorded in a
per-agent index so the listing only returns that agent's files. Without
``?agent=``, the cluster-wide ``OPENAI_API_KEY`` env var is used and uploads
are indexed under a shared env-mode key so they can still attach to /chat.
"""

from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path

from openai import APIConnectionError, APIStatusError
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, Response
from starlette.routing import Route

from .agent_credentials import parse_agent_ref, resolve_agent_openai_credentials
from .config import config
from .file_index import ENV_INDEX_KEY, get_index
from .providers import FileProvider, create_provider

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {
    ".pdf",
    ".txt", ".md", ".json", ".html", ".xml", ".css", ".js", ".ts", ".tsx", ".jsx",
    ".py", ".rb", ".java", ".c", ".cpp", ".h", ".hpp", ".cs", ".go", ".rs", ".swift",
    ".kt", ".scala", ".sh", ".bash", ".zsh", ".ps1", ".bat", ".r", ".m", ".sql",
    ".yaml", ".yml", ".toml", ".ini", ".cfg", ".conf", ".log", ".csv",
    ".doc", ".docx", ".rtf", ".odt",
    ".ppt", ".pptx",
    ".xls", ".xlsx", ".tsv",
}

_ui_html: str | None = None


def _load_ui_html() -> str:
    # Lazy-loaded so a missing static asset breaks only the UI route, not the
    # whole executor (this module is imported by app startup).
    global _ui_html
    if _ui_html is None:
        _ui_html = (Path(__file__).parent / "static" / "index.html").read_text()
    return _ui_html


def _maps_provider_errors(handler):
    """Surface upstream provider failures as structured errors, not bare 500s.

    Client-side upstream errors (4xx, e.g. expired gateway credentials) pass
    through with their status; upstream 5xx and connection failures map to 502.
    """

    async def wrapped(request: Request) -> Response:
        try:
            return await handler(request)
        except APIStatusError as e:
            status = e.status_code if 400 <= e.status_code < 500 else 502
            logger.warning("provider call failed (%s): %s", e.status_code, e.message)
            return JSONResponse(
                {"error": f"Upstream file provider error ({e.status_code}): {e.message}"},
                status_code=status,
            )
        except APIConnectionError as e:
            logger.warning("provider connection failed: %s", e)
            return JSONResponse(
                {"error": f"Could not reach the upstream file provider: {e}"},
                status_code=502,
            )

    return wrapped


def _get_env_provider() -> FileProvider:
    if not config.openai_api_key:
        raise ValueError(
            "No API key configured. Either pass ?agent=<name> on the request "
            "or set OPENAI_API_KEY env var on the executor.",
        )
    return create_provider(
        provider=config.file_provider,
        api_key=config.openai_api_key,
        base_url=config.openai_base_url or None,
    )


def _agent_param(request: Request) -> tuple[str, str] | None:
    raw = request.query_params.get("agent")
    if not raw:
        return None
    return parse_agent_ref(raw)


def _index_key(request: Request) -> str:
    agent = _agent_param(request)
    return agent[1] if agent is not None else ENV_INDEX_KEY


async def _get_provider_for_request(request: Request) -> FileProvider:
    agent = _agent_param(request)
    if agent is None:
        return _get_env_provider()

    namespace, name = agent
    creds = await resolve_agent_openai_credentials(name, namespace)
    if creds is None:
        # An explicit ?agent= that doesn't resolve is an error: falling back to
        # the env key would silently put files in a different OpenAI project
        # from the one the agent's Responses calls use.
        raise ValueError(
            f"Could not resolve OpenAI credentials for agent {namespace}/{name} "
            "(agent/Model/Secret missing or not readable by this executor's "
            "service account). Drop ?agent= to use the env-var fallback.",
        )

    api_key, base_url = creds
    return create_provider(provider="openai", api_key=api_key, base_url=base_url)


async def executor_ui(request: Request) -> Response:
    try:
        return HTMLResponse(_load_ui_html())
    except OSError:
        logger.exception("executor UI asset missing")
        return Response("Executor UI assets not available.", status_code=404)


@_maps_provider_errors
async def upload_file(request: Request) -> JSONResponse:
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > config.max_upload_bytes:
        return JSONResponse(
            {"error": f"File exceeds the {config.max_upload_bytes} byte upload limit."},
            status_code=413,
        )

    form = await request.form()
    upload = form.get("file")
    purpose = form.get("purpose", "user_data")

    if not upload:
        return JSONResponse({"error": "No file provided"}, status_code=400)

    filename = getattr(upload, "filename", "upload")
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return JSONResponse(
            {"error": f"File type '{ext}' is not supported."},
            status_code=400,
        )

    content = await upload.read()
    if len(content) > config.max_upload_bytes:
        return JSONResponse(
            {"error": f"File exceeds the {config.max_upload_bytes} byte upload limit."},
            status_code=413,
        )
    try:
        provider = await _get_provider_for_request(request)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    result = await provider.upload(filename, content, purpose)

    name = _index_key(request)
    try:
        index = get_index(config.sessions_dir)
        await asyncio.to_thread(index.add, name, result.id)
    except Exception as e:
        logger.warning("file_index add failed for %s/%s: %s", name, result.id, e)

    return JSONResponse(result.to_dict(), status_code=201)


@_maps_provider_errors
async def list_files(request: Request) -> JSONResponse:
    purpose = request.query_params.get("purpose")
    try:
        provider = await _get_provider_for_request(request)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    listing = await provider.list_files(purpose=purpose)

    name = _index_key(request)
    known_ids = {f.id for f in listing.files}
    index = get_index(config.sessions_dir)
    if listing.complete:
        survivors = set(await asyncio.to_thread(index.prune_to, name, known_ids))
    else:
        # Incomplete upstream listing (gateway without cursor pagination):
        # absence doesn't prove deletion, so filter without persisting prunes.
        survivors = known_ids & set(await asyncio.to_thread(index.list_for_agent, name))
    files = [f for f in listing.files if f.id in survivors]

    return JSONResponse({"data": [f.to_dict() for f in files], "object": "list"})


@_maps_provider_errors
async def get_file(request: Request) -> JSONResponse:
    file_id = request.path_params["file_id"]
    try:
        provider = await _get_provider_for_request(request)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    result = await provider.get(file_id)
    return JSONResponse(result.to_dict())


@_maps_provider_errors
async def delete_file(request: Request) -> JSONResponse:
    file_id = request.path_params["file_id"]
    try:
        provider = await _get_provider_for_request(request)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    result = await provider.delete(file_id)

    name = _index_key(request)
    try:
        index = get_index(config.sessions_dir)
        await asyncio.to_thread(index.remove, name, file_id)
    except Exception as e:
        logger.warning("file_index remove failed for %s/%s: %s", name, file_id, e)

    return JSONResponse(result.to_dict())


file_api_routes = [
    Route("/", executor_ui, methods=["GET"]),
    Route("/v1/files", upload_file, methods=["POST"]),
    Route("/v1/files", list_files, methods=["GET"]),
    Route("/v1/files/{file_id}", get_file, methods=["GET"]),
    Route("/v1/files/{file_id}", delete_file, methods=["DELETE"]),
]
