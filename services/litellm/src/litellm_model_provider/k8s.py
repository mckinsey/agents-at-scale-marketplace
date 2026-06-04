"""Thin Kubernetes helpers for the resources the provider owns: tenant Secrets
holding the virtual key, and Ark Model custom resources."""

from __future__ import annotations

import logging

from kubernetes import client
from kubernetes.client.rest import ApiException

from .config import MANAGED_BY

log = logging.getLogger(__name__)

ARK_GROUP = "ark.mckinsey.com"
ARK_VERSION = "v1alpha1"
MODEL_PLURAL = "models"
DASHBOARD_ICON_ANNOTATION = "ark.mckinsey.com/dashboard-icon"
# Provenance: which provider instance (namespace/name) owns this Model.
MODEL_PROVIDER_ANNOTATION = "ark.mckinsey.com/model-provider"
MANAGED_BY_LABEL = "app.kubernetes.io/managed-by"
# Records which models the tenant's key was scoped to, so we only call the
# backend to re-scope when the desired set actually changes.
MODELS_ANNOTATION = "litellm.ark.mckinsey.com/models"


def sanitize_name(model_id: str) -> str:
    """LiteLLM model ids (e.g. bedrock/anthropic.claude-3) aren't valid resource
    names. Map to RFC-1123 while keeping the original in spec.model.value."""
    out = "".join(c if c.isalnum() else "-" for c in model_id.lower())
    return out.strip("-")[:253]


class K8s:
    def __init__(self):
        self.core = client.CoreV1Api()
        self.custom = client.CustomObjectsApi()

    # ── Secrets (virtual key) ──────────────────────────────────────────────────
    def get_secret(self, namespace: str, name: str) -> client.V1Secret | None:
        try:
            return self.core.read_namespaced_secret(name, namespace)
        except ApiException as e:
            if e.status == 404:
                return None
            raise

    def upsert_vkey_secret(
        self, namespace: str, name: str, token: str, models: list[str]
    ) -> None:
        body = client.V1Secret(
            metadata=client.V1ObjectMeta(
                name=name,
                namespace=namespace,
                labels={MANAGED_BY_LABEL: MANAGED_BY},
                annotations={MODELS_ANNOTATION: ",".join(sorted(models))},
            ),
            string_data={"api-key": token},
            type="Opaque",
        )
        existing = self.get_secret(namespace, name)
        if existing is None:
            self.core.create_namespaced_secret(namespace, body)
        else:
            self.core.replace_namespaced_secret(name, namespace, body)

    # ── Model custom resources ─────────────────────────────────────────────────
    def list_managed_models(self, namespace: str) -> list[str]:
        resp = self.custom.list_namespaced_custom_object(
            ARK_GROUP,
            ARK_VERSION,
            namespace,
            MODEL_PLURAL,
            label_selector=f"{MANAGED_BY_LABEL}={MANAGED_BY}",
        )
        return [m["metadata"]["name"] for m in resp.get("items", [])]

    def upsert_model(
        self,
        namespace: str,
        model_id: str,
        base_url: str,
        vkey_secret: str,
        icon: str,
        provider_ref: str = "",
    ) -> None:
        name = sanitize_name(model_id)
        annotations = {}
        if icon:
            annotations[DASHBOARD_ICON_ANNOTATION] = icon
        if provider_ref:
            annotations[MODEL_PROVIDER_ANNOTATION] = provider_ref
        body = {
            "apiVersion": f"{ARK_GROUP}/{ARK_VERSION}",
            "kind": "Model",
            "metadata": {
                "name": name,
                "namespace": namespace,
                "labels": {MANAGED_BY_LABEL: MANAGED_BY},
                "annotations": annotations,
            },
            "spec": {
                "type": "completions",
                "provider": "openai",
                "model": {"value": model_id},
                "config": {
                    "openai": {
                        "baseUrl": {"value": base_url},
                        "apiKey": {
                            "valueFrom": {
                                "secretKeyRef": {
                                    "name": vkey_secret,
                                    "key": "api-key",
                                }
                            }
                        },
                    }
                },
            },
        }
        try:
            self.custom.create_namespaced_custom_object(
                ARK_GROUP, ARK_VERSION, namespace, MODEL_PLURAL, body
            )
            log.info("created model %s in namespace %s", name, namespace)
        except ApiException as e:
            if e.status != 409:
                raise
            # Already exists — patch quietly (happens every reconcile, so debug).
            self.custom.patch_namespaced_custom_object(
                ARK_GROUP, ARK_VERSION, namespace, MODEL_PLURAL, name, body
            )
            log.debug("patched model %s in namespace %s", name, namespace)

    def delete_model(self, namespace: str, name: str) -> None:
        try:
            self.custom.delete_namespaced_custom_object(
                ARK_GROUP, ARK_VERSION, namespace, MODEL_PLURAL, name
            )
        except ApiException as e:
            if e.status != 404:
                raise
