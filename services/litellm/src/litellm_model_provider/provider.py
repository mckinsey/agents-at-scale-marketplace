"""Reconcile loop: project LiteLLM models + a scoped virtual key into each
configured tenant namespace, and prune what no longer belongs."""

from __future__ import annotations

import logging
import time

from .backend import Backend, BackendUnavailable
from .config import Config, Target
from .k8s import K8s, MODELS_ANNOTATION, sanitize_name

log = logging.getLogger(__name__)


class Provider:
    def __init__(self, config: Config, backend: Backend, k8s: K8s):
        self.config = config
        self.backend = backend
        self.k8s = k8s

    def run(self) -> None:
        log.info(
            "starting reconcile loop: %d target(s), interval=%ds",
            len(self.config.targets),
            self.config.reconcile_interval_seconds,
        )
        while True:
            try:
                self.reconcile_once()
            except Exception:  # keep the loop alive; transient API/LLM errors recover next tick
                log.exception("reconcile failed; retrying next interval")
            time.sleep(self.config.reconcile_interval_seconds)

    def reconcile_once(self) -> None:
        try:
            available = self.backend.list_models()
        except BackendUnavailable as e:
            # Common at startup before the proxy is ready — one clean line, no trace.
            log.warning(
                "LiteLLM not reachable at %s yet (%s); retrying in %ds",
                self.config.litellm_base_url,
                e,
                self.config.reconcile_interval_seconds,
            )
            return
        for target in self.config.targets:
            try:
                self._reconcile_target(target, available)
            except Exception:
                log.exception("reconcile failed for namespace %s", target.namespace)

    def _reconcile_target(self, target: Target, available: list[str]) -> None:
        # An empty allow-list means "all available models", and the key is minted
        # unrestricted so newly-added models need no key change.
        desired = target.models or available
        unknown = set(target.models) - set(available)
        if unknown:
            log.warning(
                "namespace %s requests models not on LiteLLM: %s",
                target.namespace,
                ", ".join(sorted(unknown)),
            )
        desired = [m for m in desired if m in available]
        key_scope = target.models  # [] => unrestricted key

        self._ensure_key(target.namespace, key_scope)
        self._project_models(target.namespace, desired)
        self._prune_models(target.namespace, desired)

    def _ensure_key(self, namespace: str, scope: list[str]) -> None:
        secret = self.k8s.get_secret(namespace, self.config.vkey_secret_name)
        alias = f"ark-{namespace}"
        if secret is None:
            token = self.backend.create_key(alias, scope)
            self.k8s.upsert_vkey_secret(
                namespace, self.config.vkey_secret_name, token, scope
            )
            log.info("minted virtual key for namespace %s", namespace)
            return

        # Re-scope only when the desired set changed (skip for unrestricted keys).
        prev = (secret.metadata.annotations or {}).get(MODELS_ANNOTATION, "")
        if scope and prev != ",".join(sorted(scope)):
            token = (secret.string_data or {}).get("api-key") or _decode(secret)
            self.backend.update_key(token, scope)
            self.k8s.upsert_vkey_secret(
                namespace, self.config.vkey_secret_name, token, scope
            )
            log.info("re-scoped virtual key for namespace %s", namespace)

    def _project_models(self, namespace: str, models: list[str]) -> None:
        for model_id in models:
            self.k8s.upsert_model(
                namespace,
                model_id,
                self.config.litellm_base_url,
                self.config.vkey_secret_name,
                self.config.model_icon,
                self.config.provider_ref,
            )

    def _prune_models(self, namespace: str, desired: list[str]) -> None:
        wanted = {sanitize_name(m) for m in desired}
        for name in self.k8s.list_managed_models(namespace):
            if name not in wanted:
                self.k8s.delete_model(namespace, name)
                log.info("pruned model %s from namespace %s", name, namespace)


def _decode(secret) -> str:
    import base64

    return base64.b64decode((secret.data or {}).get("api-key", "")).decode()
