"""Model-source backends.

A backend knows how to (a) list the models a source exposes and (b) issue/scope a
credential. LiteLLM is the first implementation; an AI gateway or another proxy
would implement the same interface, keeping the reconcile loop backend-agnostic.

Idempotency note: "does this tenant already have a key" is answered by the
Kubernetes Secret (which the provider owns), not by querying the backend — so
backends only need create/update, not lookup.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

import httpx


class BackendUnavailable(Exception):
    """The model source could not be reached (e.g. the proxy isn't ready yet)."""


class Backend(ABC):
    @abstractmethod
    def list_models(self) -> list[str]:
        """Model identifiers the source currently exposes."""

    @abstractmethod
    def create_key(self, alias: str, models: list[str]) -> str:
        """Mint a credential scoped to `models`. Empty list = access to all
        models, so models added to the source later are authorized without
        re-issuing the key."""

    @abstractmethod
    def update_key(self, token: str, models: list[str]) -> None:
        """Realign an existing credential's model scope."""


class LiteLLMBackend(Backend):
    def __init__(self, base_url: str, master_key: str, timeout: float = 10.0):
        self._client = httpx.Client(
            base_url=base_url.rstrip("/"),
            headers={"Authorization": f"Bearer {master_key}"},
            timeout=timeout,
        )

    def list_models(self) -> list[str]:
        # This is the first call each tick; a connect error here means the proxy
        # isn't up yet. Translate to BackendUnavailable so the loop logs cleanly.
        try:
            resp = self._client.get("/v1/models")
            resp.raise_for_status()
        except httpx.HTTPError as e:
            raise BackendUnavailable(str(e)) from e
        return [m["id"] for m in resp.json().get("data", [])]

    def create_key(self, alias: str, models: list[str]) -> str:
        resp = self._client.post(
            "/key/generate", json={"key_alias": alias, "models": models}
        )
        resp.raise_for_status()
        return resp.json()["key"]

    def update_key(self, token: str, models: list[str]) -> None:
        self._client.post(
            "/key/update", json={"key": token, "models": models}
        ).raise_for_status()
