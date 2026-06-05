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
from dataclasses import dataclass
from typing import Any

from ark_sdk.client import V1_ALPHA1, with_ark_client
from ark_sdk.k8s import SecretClient
from kubernetes_asyncio import client as k8s_client
from kubernetes_asyncio import config as k8s_config
from kubernetes_asyncio.client.api_client import ApiClient

logger = logging.getLogger(__name__)


def _ensure_k8s_config() -> None:
    # kubernetes_asyncio.ApiClient() (used by both SecretClient and CoreV1Api)
    # reads from the global configuration object. load_incluster_config() must
    # be called before any ApiClient is constructed — it is not called
    # automatically when running inside a pod. We call it on every use rather
    # than caching the result so that rotated service account tokens are always
    # picked up from disk.
    k8s_config.load_incluster_config()


@dataclass
class AgentContext:
    """Everything needed to chat with an agent without going through Ark.

    Filled in by ``resolve_agent_context``. Lets the executor's /chat
    endpoint talk to the same OpenAI project / model / system prompt the
    agent would use when invoked via a Query CR.
    """

    api_key: str
    base_url: str | None
    model_name: str
    instructions: str  # the agent's spec.prompt


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
        _ensure_k8s_config()
        sc = SecretClient(namespace=namespace)
        res = await sc.get_secret_value(name, key)
        return base64.b64decode(res["value"]).decode("utf-8")
    except Exception as e:
        # Swallowing here would surface as a baffling "apiKey resolved empty";
        # name the failing Secret instead.
        raise ValueError(f"Failed to read Secret {namespace}/{name} key '{key}': {e}") from e


async def _resolve_configmap(cm_ref: Any, namespace: str) -> str:
    name = _attr_or_key(cm_ref, "name")
    key = _attr_or_key(cm_ref, "key")
    if not (name and key):
        return ""
    try:
        _ensure_k8s_config()
        async with ApiClient() as api:
            v1 = k8s_client.CoreV1Api(api)
            cm = await v1.read_namespaced_config_map(name=name, namespace=namespace)
            return (cm.data or {}).get(key, "")
    except Exception as e:
        raise ValueError(f"Failed to read ConfigMap {namespace}/{name} key '{key}': {e}") from e


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
    return os.getenv("POD_NAMESPACE") or os.getenv("ARK_NAMESPACE") or "default"


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

    Returns None when the agent has no OpenAI model (semantic absence);
    raises ValueError when resolution fails (not found, RBAC, bad refs).
    """
    ctx = await resolve_agent_context(agent_name, namespace)
    if ctx is None:
        return None
    return ctx.api_key, ctx.base_url


async def resolve_agent_context(agent_name: str, namespace: str) -> AgentContext | None:
    """Resolve the full chat context for an agent from k8s.

    Reads the Agent CR's modelRef + prompt, then its Model CR's openai
    config (apiKey, baseUrl).

    Returns None only when the agent simply has no usable model (no
    modelRef, or a Model without openai config) — semantic absence the
    caller may fall back from. Misconfiguration raises ValueError with a
    message fit for the caller; everything else (RBAC, network, bugs)
    propagates — flattening those into None hid real failures behind
    silent credential fallbacks.
    """
    try:
        async with with_ark_client(namespace, V1_ALPHA1) as ark:
            try:
                agent = await ark.agents.a_get(agent_name, namespace)
            except ValueError:
                raise
            except Exception as e:
                raise _k8s_error("Agent", f"{namespace}/{agent_name}", e) from e
            model_ref = _attr_or_key(agent.spec, "model_ref", "modelRef")
            if not model_ref:
                logger.info("agent %s/%s has no modelRef", namespace, agent_name)
                return None
            model_ref_name = _attr_or_key(model_ref, "name")
            model_ns = _attr_or_key(model_ref, "namespace") or namespace
            if not model_ref_name:
                return None
            try:
                model = await ark.models.a_get(model_ref_name, model_ns)
            except ValueError:
                raise
            except Exception as e:
                raise _k8s_error("Model", f"{model_ns}/{model_ref_name}", e) from e
            cfg = _attr_or_key(model.spec, "config")
            openai_cfg = _attr_or_key(cfg, "openai")
            if not openai_cfg:
                logger.info(
                    "model %s/%s has no openai config; cannot resolve credentials",
                    model_ns,
                    model_ref_name,
                )
                return None
            api_key_vs = _attr_or_key(openai_cfg, "api_key", "apiKey")
            base_url_vs = _attr_or_key(openai_cfg, "base_url", "baseUrl")
            api_key = await _resolve_value_source(api_key_vs, model_ns)
            base_url = await _resolve_value_source(base_url_vs, model_ns)
            if not api_key:
                raise ValueError(
                    f"Model {model_ns}/{model_ref_name} openai apiKey resolved "
                    "empty (missing Secret/ConfigMap key?)"
                )
            instructions = _attr_or_key(agent.spec, "prompt") or ""
            # The API-side model id lives in spec.model (a ValueSource); the
            # CR name is just a DNS-1123 k8s identifier (e.g. CR "gpt-5-4"
            # vs model id "gpt-5.4-2026-03-05") and gateways reject it.
            model_vs = _attr_or_key(model.spec, "model")
            model_id = await _resolve_value_source(model_vs, model_ns) or model_ref_name
            return AgentContext(
                api_key=api_key,
                base_url=base_url or None,
                model_name=model_id,
                instructions=instructions,
            )
    except ValueError:
        raise
    except Exception:
        logger.exception(
            "agent %s/%s context resolution failed", namespace, agent_name
        )
        raise


def _k8s_error(kind: str, ref: str, e: Exception) -> ValueError:
    # ark-sdk wraps kubernetes ApiException in a bare Exception whose text
    # carries the status, so classify from both the attribute and the text.
    status = getattr(e, "status", None)
    text = str(e)
    if status == 404 or "(404)" in text or "Not Found" in text:
        return ValueError(f"{kind} {ref} not found")
    if status == 403 or "(403)" in text or "Forbidden" in text:
        return ValueError(
            f"Access to {kind} {ref} forbidden — the executor's service "
            "account RBAC is namespace-scoped; cross-namespace refs are not "
            "readable"
        )
    return ValueError(f"Failed to read {kind} {ref}: {e}")
