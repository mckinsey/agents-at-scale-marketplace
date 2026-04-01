"""
Speech MCP Server

Local audio transcription via OpenAI Whisper, exposed as an MCP tool
over StreamableHTTP for ARK integration.
"""

import asyncio
import hashlib
import json
import logging
import os
import uuid

import whisper
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, PlainTextResponse, Response
from starlette.routing import Route

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

PORT = int(os.environ.get("PORT", "8080"))
BASE_DATA_DIR = os.environ.get("BASE_DATA_DIR", "/data")
WHISPER_MODEL = os.environ.get("WHISPER_MODEL", "small")
CACHE_DIR = os.environ.get("CACHE_DIR", "/data/whisper-cache")

SUPPORTED_EXTENSIONS = {".mp3", ".mp4", ".m4a", ".wav", ".ogg", ".flac", ".webm"}

_whisper_model = None


def get_whisper_model():
    """Lazy-load the Whisper model."""
    global _whisper_model
    if _whisper_model is None:
        logger.info("Loading Whisper model '%s'...", WHISPER_MODEL)
        _whisper_model = whisper.load_model(WHISPER_MODEL)
        logger.info("Whisper model loaded successfully.")
    return _whisper_model


def transcribe_audio(file_path: str) -> str:
    """Transcribe an audio file using Whisper. Results are cached by file path."""
    if not os.path.isabs(file_path):
        file_path = os.path.join(BASE_DATA_DIR, file_path)

    full_path = os.path.abspath(file_path)
    logger.info("Transcribing: %s", full_path)

    if not os.path.isfile(full_path):
        raise FileNotFoundError(f"Audio file not found: {file_path}")

    ext = os.path.splitext(full_path)[1].lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported format '{ext}'. Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}")

    os.makedirs(CACHE_DIR, exist_ok=True)
    cache_key = hashlib.sha256(full_path.encode()).hexdigest()[:16]
    cache_file = os.path.join(CACHE_DIR, f"{cache_key}.txt")

    if os.path.isfile(cache_file):
        logger.info("Cache hit for %s", full_path)
        with open(cache_file, "r") as f:
            return f.read()

    result = get_whisper_model().transcribe(full_path, verbose=False)
    transcript = " ".join(seg["text"] for seg in result.get("segments", [])).strip()

    with open(cache_file, "w") as f:
        f.write(transcript)

    logger.info("Transcription complete: %d characters", len(transcript))
    return transcript


# ---------------------------------------------------------------------------
# MCP protocol
# ---------------------------------------------------------------------------

TOOL_DEFINITION = {
    "name": "transcribe_audio",
    "description": (
        "Transcribe an audio file to text using speech-to-text. "
        "Accepts: mp3, m4a, mp4, wav, ogg, flac, webm. "
        "Returns the full text transcription. "
        "file_path is relative to the shared data directory."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Path to the audio file to transcribe",
            }
        },
        "required": ["file_path"],
    },
}

SERVER_INFO = {"name": "speech-mcp-server", "version": "0.1.0"}
CAPABILITIES = {"tools": {"listChanged": False}}


def _tool_result(text: str, is_error: bool = False) -> dict:
    return {"content": [{"type": "text", "text": text}], "isError": is_error}


def handle_initialize(params: dict) -> dict:
    return {"protocolVersion": "2024-11-05", "capabilities": CAPABILITIES, "serverInfo": SERVER_INFO}


def handle_tools_list(params: dict) -> dict:
    return {"tools": [TOOL_DEFINITION]}


def handle_tool_call(params: dict) -> dict:
    if params.get("name") != "transcribe_audio":
        return _tool_result(f"Unknown tool: {params.get('name')}", is_error=True)

    file_path = params.get("arguments", {}).get("file_path", "")
    if not file_path:
        return _tool_result("Error: file_path is required", is_error=True)

    try:
        return _tool_result(transcribe_audio(file_path))
    except (FileNotFoundError, ValueError) as e:
        return _tool_result(f"Error: {e}", is_error=True)
    except Exception as e:
        logger.exception("Transcription failed")
        return _tool_result(f"Transcription error: {e}", is_error=True)


METHOD_HANDLERS = {
    "initialize": handle_initialize,
    "tools/list": handle_tools_list,
    "tools/call": handle_tool_call,
    "notifications/initialized": lambda _: None,
    "ping": lambda _: {},
}


# ---------------------------------------------------------------------------
# HTTP layer
# ---------------------------------------------------------------------------

_sessions: dict[str, bool] = {}


def _json_response(data, status_code=200, headers=None):
    """JSON response with byte-accurate Content-Length."""
    body = json.dumps(data, ensure_ascii=True).encode("utf-8")
    h = {"content-type": "application/json"}
    if headers:
        h.update(headers)
    return Response(content=body, status_code=status_code, headers=h)


def _session_headers(session_id: str | None) -> dict:
    return {"Mcp-Session-Id": session_id} if session_id else {}


def process_jsonrpc(msg: dict, session_id: str | None) -> dict | None:
    """Process a single JSON-RPC message."""
    method = msg.get("method", "")
    msg_id = msg.get("id")
    params = msg.get("params", {})
    is_notification = msg_id is None

    handler = METHOD_HANDLERS.get(method)
    if handler is None:
        if is_notification:
            return None
        return {"jsonrpc": "2.0", "error": {"code": -32601, "message": f"Method not found: {method}"}, "id": msg_id}

    try:
        result = handler(params)
        if is_notification:
            return None

        if method == "initialize" and not session_id:
            sid = str(uuid.uuid4())
            _sessions[sid] = True
            logger.info("New session: %s", sid)

        return {"jsonrpc": "2.0", "result": result, "id": msg_id}
    except Exception as e:
        logger.exception("Error handling %s", method)
        if is_notification:
            return None
        return {"jsonrpc": "2.0", "error": {"code": -32603, "message": str(e)}, "id": msg_id}


async def handle_mcp(request: Request):
    """POST /mcp -- MCP JSON-RPC over StreamableHTTP."""
    session_id = request.headers.get("mcp-session-id")

    try:
        body = await request.json()
    except Exception:
        return _json_response(
            {"jsonrpc": "2.0", "error": {"code": -32700, "message": "Parse error"}, "id": None},
            status_code=400,
        )

    if isinstance(body, list):
        responses = [r for item in body if (r := await asyncio.to_thread(process_jsonrpc, item, session_id))]
        if not responses:
            return Response(status_code=204)
        return _json_response(responses, headers=_session_headers(session_id))

    resp = await asyncio.to_thread(process_jsonrpc, body, session_id)
    if resp is None:
        return Response(status_code=204)
    return _json_response(resp, headers=_session_headers(session_id))


async def handle_mcp_get(request: Request):
    return JSONResponse({"jsonrpc": "2.0", "error": {"code": -32000, "message": "Use POST"}}, status_code=405)


async def handle_health(request: Request):
    return PlainTextResponse("OK")


app = Starlette(
    routes=[
        Route("/mcp", handle_mcp, methods=["POST"]),
        Route("/mcp", handle_mcp_get, methods=["GET"]),
        Route("/health", handle_health, methods=["GET"]),
    ],
)

if __name__ == "__main__":
    import uvicorn

    logger.info("Starting Speech MCP Server on port %d (model=%s)", PORT, WHISPER_MODEL)
    uvicorn.run(app, host="0.0.0.0", port=PORT)
