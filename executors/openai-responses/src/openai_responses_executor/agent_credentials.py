"""Resolve OpenAI credentials from an Ark Agent's referenced Model.

The Files API endpoints use this when a request specifies which agent the
upload is for, so that uploads happen under the same OpenAI project/key the
agent's Responses calls will use. Without it the executor would use the
cluster-wide env var, which silently breaks file_id resolution whenever the
agent's Model points at a different OpenAI project (different gateway UUID,
different account, etc.).
"""

from __future__ import annotations

import base64
import logging
import os
from typing import Any

from ark_sdk.client import V1_ALPHA1, with_ark_client
from ark_sdk.k8s import SecretClient
from kubernetes_asyncio import client as k8s_client
from kubernetes_asyncio.client.api_client import ApiClient

logger = logging.getLogger(__name__)


def _attr_or_key(obj: Any, attr: str, key: str | None = None) -> Any:
    if obj is None:
        return None
    if isinstance(obj, dict):
        return obj.get(key or attr)
    return getattr(obj, attr, None)


async def _resolve_secret(secret_ref: Any, namespace: str) -> str:
    name = _attr_or_key(secret_ref, "name")
    key = _attr_or_key(secret_ref, "key")
    if not (name and key):
        return ""
    try:
        sc = SecretClient(namespace=namespace)
        res = await sc.get_secret_value(name, key)
        return base64.b64decode(res["value"]).decode("utf-8")
    except Exception as e:
        logger.warning("secret %s/%s resolution failed: %s", name, key, e)
        return ""


async def _resolve_configmap(cm_ref: Any, namespace: str) -> str:
    name = _attr_or_key(cm_ref, "name")
    key = _attr_or_key(cm_ref, "key")
    if not (name and key):
        return ""
    try:
        async with ApiClient() as api:
            v1 = k8s_client.CoreV1Api(api)
            cm = await v1.read_namespaced_config_map(name=name, namespace=namespace)
            return (cm.data or {}).get(key, "")
    except Exception as e:
        logger.warning("configmap %s/%s resolution failed: %s", name, key, e)
        return ""


async def _resolve_value_source(vs: Any, namespace: str) -> str:
    if vs is None:
        return ""
    direct = _attr_or_key(vs, "value")
    if direct:
        return direct
    vf = _attr_or_key(vs, "value_from", "valueFrom")
    if not vf:
        return ""
    secret = _attr_or_key(vf, "secret_key_ref", "secretKeyRef")
    if secret:
        val = await _resolve_secret(secret, namespace)
        if val:
            return val
    cm = _attr_or_key(vf, "config_map_key_ref", "configMapKeyRef")
    if cm:
        return await _resolve_configmap(cm, namespace)
    return ""


def _default_namespace() -> str:
    return (
        os.getenv("POD_NAMESPACE")
        or os.getenv("ARK_NAMESPACE")
        or "default"
    )


def parse_agent_ref(value: str) -> tuple[str, str]:
    """Parse 'namespace/name' or 'name' into (namespace, name)."""
    if "/" in value:
        ns, name = value.split("/", 1)
        return ns or _default_namespace(), name
    return _default_namespace(), value


async def resolve_agent_openai_credentials(
    agent_name: str, namespace: str
) -> tuple[str, str | None] | None:
    """Return (api_key, base_url) for the OpenAI Model used by an agent.

    Returns None if the agent has no model, the model isn't OpenAI, or the
    api key can't be resolved.
    """
    try:
        async with with_ark_client(namespace, V1_ALPHA1) as ark:
            agent = await ark.agents.a_get(agent_name, namespace)
            model_ref = _attr_or_key(agent.spec, "model_ref", "modelRef")
            if not model_ref:
                logger.info("agent %s/%s has no modelRef", namespace, agent_name)
                return None
            model_name = _attr_or_key(model_ref, "name")
            model_ns = _attr_or_key(model_ref, "namespace") or namespace
            if not model_name:
                return None
            model = await ark.models.a_get(model_name, model_ns)
            cfg = _attr_or_key(model.spec, "config")
            openai_cfg = _attr_or_key(cfg, "openai")
            if not openai_cfg:
                logger.info(
                    "model %s/%s has no openai config; cannot resolve files credentials",
                    model_ns,
                    model_name,
                )
                return None
            api_key_vs = _attr_or_key(openai_cfg, "api_key", "apiKey")
            base_url_vs = _attr_or_key(openai_cfg, "base_url", "baseUrl")
            api_key = await _resolve_value_source(api_key_vs, model_ns)
            base_url = await _resolve_value_source(base_url_vs, model_ns)
            if not api_key:
                logger.warning(
                    "model %s/%s openai apiKey resolution returned empty",
                    model_ns,
                    model_name,
                )
                return None
            return api_key, base_url or None
    except Exception as e:
        logger.warning(
            "agent %s/%s credential resolution failed: %s",
            namespace,
            agent_name,
            e,
        )
        return None
