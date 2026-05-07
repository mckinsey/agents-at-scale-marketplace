"""OpenAI-compatible Files API proxy.

Proxies file operations to the OpenAI Files API so the UI can upload files
and receive real OpenAI file_ids that the executor passes through to the
Responses API as input_file content parts.
"""

import logging
from typing import Any

from openai import AsyncOpenAI
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from .config import config

logger = logging.getLogger(__name__)


def _get_client(api_key: str | None = None) -> AsyncOpenAI:
    key = api_key or config.openai_api_key
    if not key:
        raise ValueError("No OpenAI API key configured. Set OPENAI_API_KEY env var.")
    return AsyncOpenAI(api_key=key)


async def upload_file(request: Request) -> JSONResponse:
    """POST /v1/files — upload a file to OpenAI."""
    form = await request.form()
    upload = form.get("file")
    purpose = form.get("purpose", "user_data")

    if not upload:
        return JSONResponse({"error": "No file provided"}, status_code=400)

    content = await upload.read()
    filename = getattr(upload, "filename", "upload")

    client = _get_client()
    result = await client.files.create(
        file=(filename, content),
        purpose=purpose,
    )

    return JSONResponse(result.model_dump(), status_code=201)


async def list_files(request: Request) -> JSONResponse:
    """GET /v1/files — list uploaded files."""
    purpose = request.query_params.get("purpose")
    client = _get_client()

    kwargs: dict[str, Any] = {}
    if purpose:
        kwargs["purpose"] = purpose

    result = await client.files.list(**kwargs)
    return JSONResponse({"data": [f.model_dump() for f in result.data], "object": "list"})


async def get_file(request: Request) -> JSONResponse:
    """GET /v1/files/{file_id} — retrieve file metadata."""
    file_id = request.path_params["file_id"]
    client = _get_client()
    result = await client.files.retrieve(file_id)
    return JSONResponse(result.model_dump())


async def delete_file(request: Request) -> JSONResponse:
    """DELETE /v1/files/{file_id} — delete a file."""
    file_id = request.path_params["file_id"]
    client = _get_client()
    result = await client.files.delete(file_id)
    return JSONResponse(result.model_dump())


file_api_routes = [
    Route("/v1/files", upload_file, methods=["POST"]),
    Route("/v1/files", list_files, methods=["GET"]),
    Route("/v1/files/{file_id}", get_file, methods=["GET"]),
    Route("/v1/files/{file_id}", delete_file, methods=["DELETE"]),
]
