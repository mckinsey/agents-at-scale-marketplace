"""Conversation session state persisted on the executor's PVC.

One directory per conversation under SESSIONS_DIR:

    <conversation_id>/response_id   — last OpenAI response id (threading)
    <conversation_id>/file_ids      — JSON array of file IDs already attached

Both the A2A executor and the UI /chat endpoint share this store so threading
behaves identically on either path. Tracking attached file IDs lets
continuation turns attach only files that are new to the conversation —
re-attaching IDs already in the threaded response state duplicates
input_file parts, while skipping new ones silently drops attachments.

All public functions are async and run the blocking PVC I/O in a worker
thread so handlers and SSE generators never stall the event loop.
"""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path

from .config import config

logger = logging.getLogger(__name__)


def _conv_dir(conversation_id: str) -> Path:
    return config.sessions_dir / conversation_id


def _read_response_id(conversation_id: str) -> str | None:
    path = _conv_dir(conversation_id) / "response_id"
    if path.exists():
        return path.read_text().strip() or None
    return None


def _write_response_id(conversation_id: str, response_id: str) -> None:
    d = _conv_dir(conversation_id)
    d.mkdir(parents=True, exist_ok=True)
    (d / "response_id").write_text(response_id)


def _read_sent_file_ids(conversation_id: str) -> set[str]:
    path = _conv_dir(conversation_id) / "file_ids"
    if not path.exists():
        return set()
    try:
        value = json.loads(path.read_text() or "[]")
        return {fid for fid in value if isinstance(fid, str)}
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("session file_ids load failed (%s); treating as empty", e)
        return set()


def _write_sent_file_ids(conversation_id: str, file_ids: set[str]) -> None:
    d = _conv_dir(conversation_id)
    d.mkdir(parents=True, exist_ok=True)
    (d / "file_ids").write_text(json.dumps(sorted(file_ids)))


def _clear(conversation_id: str) -> None:
    for name in ("response_id", "file_ids"):
        path = _conv_dir(conversation_id) / name
        if path.exists():
            path.unlink()


async def get_previous_response_id(conversation_id: str) -> str | None:
    return await asyncio.to_thread(_read_response_id, conversation_id)


async def save_response_id(conversation_id: str, response_id: str) -> None:
    await asyncio.to_thread(_write_response_id, conversation_id, response_id)


async def get_sent_file_ids(conversation_id: str) -> set[str]:
    return await asyncio.to_thread(_read_sent_file_ids, conversation_id)


async def mark_file_ids_sent(conversation_id: str, file_ids: set[str]) -> None:
    if not file_ids:
        return
    sent = await asyncio.to_thread(_read_sent_file_ids, conversation_id)
    await asyncio.to_thread(_write_sent_file_ids, conversation_id, sent | file_ids)


async def clear_conversation(conversation_id: str) -> None:
    await asyncio.to_thread(_clear, conversation_id)


def is_zdr_threading_error(error: Exception) -> bool:
    """True when the provider rejected previous_response_id because the org
    runs Zero Data Retention (no server-side response state is kept)."""
    text = str(error)
    return "previous_response_id" in text and "Zero Data Retention" in text


ZDR_HINT = (
    "This OpenAI organization runs Zero Data Retention, so conversation "
    "threading via previous_response_id is not supported. The stored "
    "conversation state has been reset — retry the request and it will run "
    "as a fresh turn (files will re-attach)."
)
