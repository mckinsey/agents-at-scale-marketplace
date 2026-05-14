"""Provider-agnostic Files API + upload UI.

Exposes:
    GET  /files              → upload UI (HTML)
    POST /v1/files           → upload (multipart: file, purpose)
    GET  /v1/files           → list
    GET  /v1/files/{file_id} → metadata
    DELETE /v1/files/{file_id}

All endpoints accept ``?agent=<namespace>/<name>`` (or ``<name>``). When set,
credentials are resolved from the agent's Model CR so uploads land in the same
OpenAI project the agent's Responses calls will use. Uploads/deletes are also
recorded in a per-agent index so the listing only returns this agent's files.
Without ``?agent=``, the cluster-wide ``OPENAI_API_KEY`` env var is used and
the listing returns every file the key can see.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse
from starlette.routing import Route

from .agent_credentials import parse_agent_ref, resolve_agent_openai_credentials
from .config import config
from .file_index import get_index
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

_UI_HTML = (Path(__file__).parent / "static" / "index.html").read_text()

_env_provider: FileProvider | None = None
_agent_provider_cache: dict[tuple[str, str], FileProvider] = {}


def _get_env_provider() -> FileProvider:
    global _env_provider
    if _env_provider is None:
        if not config.openai_api_key:
            raise ValueError(
                "No API key configured. Either pass ?agent=<name> on the request "
                "or set OPENAI_API_KEY env var on the executor.",
            )
        _env_provider = create_provider(
            provider=config.file_provider,
            api_key=config.openai_api_key,
            base_url=config.openai_base_url or None,
        )
    return _env_provider


def _agent_param(request: Request) -> tuple[str, str] | None:
    raw = request.query_params.get("agent")
    if not raw:
        return None
    return parse_agent_ref(raw)


async def _get_provider_for_request(request: Request) -> FileProvider:
    agent = _agent_param(request)
    if agent is None:
        return _get_env_provider()

    cached = _agent_provider_cache.get(agent)
    if cached is not None:
        return cached

    namespace, name = agent
    creds = await resolve_agent_openai_credentials(name, namespace)
    if creds is None:
        logger.warning(
            "Could not resolve OpenAI credentials for agent %s/%s; "
            "falling back to env var provider.",
            namespace,
            name,
        )
        return _get_env_provider()

    api_key, base_url = creds
    provider = create_provider(provider="openai", api_key=api_key, base_url=base_url)
    _agent_provider_cache[agent] = provider
    return provider


async def file_ui(request: Request) -> HTMLResponse:
    return HTMLResponse(_UI_HTML)


async def upload_file(request: Request) -> JSONResponse:
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
    try:
        provider = await _get_provider_for_request(request)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    result = await provider.upload(filename, content, purpose)

    agent = _agent_param(request)
    if agent is not None:
        _, name = agent
        try:
            get_index(config.sessions_dir).add(name, result.id)
        except Exception as e:
            logger.warning("file_index add failed for %s/%s: %s", name, result.id, e)

    return JSONResponse(result.to_dict(), status_code=201)


async def list_files(request: Request) -> JSONResponse:
    purpose = request.query_params.get("purpose")
    try:
        provider = await _get_provider_for_request(request)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    files = await provider.list_files(purpose=purpose)

    agent = _agent_param(request)
    if agent is not None:
        _, name = agent
        known_ids = {f.id for f in files}
        survivors = set(get_index(config.sessions_dir).prune_to(name, known_ids))
        files = [f for f in files if f.id in survivors]

    return JSONResponse({"data": [f.to_dict() for f in files], "object": "list"})


async def get_file(request: Request) -> JSONResponse:
    file_id = request.path_params["file_id"]
    try:
        provider = await _get_provider_for_request(request)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    result = await provider.get(file_id)
    return JSONResponse(result.to_dict())


async def delete_file(request: Request) -> JSONResponse:
    file_id = request.path_params["file_id"]
    try:
        provider = await _get_provider_for_request(request)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    result = await provider.delete(file_id)

    agent = _agent_param(request)
    if agent is not None:
        _, name = agent
        try:
            get_index(config.sessions_dir).remove(name, file_id)
        except Exception as e:
            logger.warning("file_index remove failed for %s/%s: %s", name, file_id, e)

    return JSONResponse(result.to_dict())


file_api_routes = [
    Route("/files", file_ui, methods=["GET"]),
    Route("/v1/files", upload_file, methods=["POST"]),
    Route("/v1/files", list_files, methods=["GET"]),
    Route("/v1/files/{file_id}", get_file, methods=["GET"]),
    Route("/v1/files/{file_id}", delete_file, methods=["DELETE"]),
]
