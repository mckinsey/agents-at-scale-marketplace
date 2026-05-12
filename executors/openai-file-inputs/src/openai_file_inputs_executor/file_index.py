"""Per-agent file index persisted on the executor's PVC.

OpenAI's `/v1/files` endpoint lists every file the API key has access to, which
on a shared gateway is effectively the whole org. Rather than leaking thousands
of unrelated uploads to every dashboard user, we maintain a side index here:
each upload records which agent uploaded it; list/delete operate against that
slice. The index lives at SESSIONS_DIR/file_index.json and survives pod
restarts (the PVC outlives the pod).

The OpenAI account is still the canonical store. We never invent a file_id —
we just remember which ones belong to which agent so the dashboard can render
the right subset.
"""

from __future__ import annotations

import json
import logging
import threading
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Process-wide lock — Starlette runs handlers on a single asyncio loop so writes
# don't actually race, but multiple replicas would; if we ever scale beyond 1
# pod the index needs a real backend. Today: 1 replica, file-level safety only.
_lock = threading.Lock()


class FileIndex:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _load(self) -> dict[str, list[str]]:
        if not self.path.exists():
            return {}
        try:
            data = json.loads(self.path.read_text() or "{}")
            if not isinstance(data, dict):
                return {}
            # Coerce values to list[str].
            return {
                str(k): [str(x) for x in (v or []) if isinstance(x, str)]
                for k, v in data.items()
            }
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("file_index load failed (%s); starting empty", e)
            return {}

    def _save(self, data: dict[str, list[str]]) -> None:
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(json.dumps(data, indent=2))
        tmp.replace(self.path)

    def list_for_agent(self, agent: str) -> list[str]:
        with _lock:
            return list(self._load().get(agent, []))

    def add(self, agent: str, file_id: str) -> None:
        with _lock:
            data = self._load()
            existing = data.setdefault(agent, [])
            if file_id not in existing:
                existing.append(file_id)
            self._save(data)

    def remove(self, agent: str, file_id: str) -> None:
        with _lock:
            data = self._load()
            if agent in data and file_id in data[agent]:
                data[agent] = [x for x in data[agent] if x != file_id]
                if not data[agent]:
                    del data[agent]
                self._save(data)

    def prune_to(self, agent: str, known_ids: set[str]) -> list[str]:
        """Drop file IDs no longer present upstream; return surviving IDs."""
        with _lock:
            data = self._load()
            current = data.get(agent, [])
            survivors = [fid for fid in current if fid in known_ids]
            if survivors != current:
                if survivors:
                    data[agent] = survivors
                elif agent in data:
                    del data[agent]
                self._save(data)
            return survivors


def get_index(sessions_dir: Any) -> FileIndex:
    return FileIndex(Path(sessions_dir) / "file_index.json")
