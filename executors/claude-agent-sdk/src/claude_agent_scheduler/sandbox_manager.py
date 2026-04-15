"""Sandbox lifecycle management with K8s-native state and local cache."""

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from kubernetes_asyncio import client, config, watch
from opentelemetry import trace
from opentelemetry.trace import StatusCode

from .config import SchedulerConfig

logger = logging.getLogger(__name__)

tracer = trace.get_tracer("claude-agent-scheduler")

# agent-sandbox CRD coordinates
SANDBOX_API_GROUP = "agents.x-k8s.io"
SANDBOX_API_VERSION = "v1alpha1"
SANDBOX_PLURAL = "sandboxes"

CLAIM_API_GROUP = "extensions.agents.x-k8s.io"
CLAIM_API_VERSION = "v1alpha1"
CLAIM_PLURAL = "sandboxclaims"

LABEL_CONVERSATION_ID = "ark.mckinsey.com/conversation-id"
LABEL_MANAGED_BY = "ark.mckinsey.com/managed-by"
MANAGED_BY_VALUE = "claude-agent-sdk-scheduler"
ANNOTATION_LAST_ACTIVITY = "ark.mckinsey.com/last-activity"

CACHE_TTL = 5.0  # seconds


class SandboxCapacityError(Exception):
    """Raised when sandbox creation is rejected due to capacity limits."""


@dataclass
class SandboxInfo:
    """Conversation-to-sandbox mapping entry."""

    claim_name: str
    sandbox_name: str
    service_fqdn: str


# ---------------------------------------------------------------------------
# Local cache — pure performance optimization, not authoritative
# ---------------------------------------------------------------------------

class SandboxCache:
    """TTL-based local cache for sandbox routing info."""

    def __init__(self, ttl: float = CACHE_TTL) -> None:
        self._ttl = ttl
        self._entries: dict[str, tuple[SandboxInfo, float]] = {}

    def get(self, conversation_id: str) -> SandboxInfo | None:
        entry = self._entries.get(conversation_id)
        if entry is None:
            return None
        info, ts = entry
        if (time.monotonic() - ts) > self._ttl:
            del self._entries[conversation_id]
            return None
        return info

    def put(self, conversation_id: str, info: SandboxInfo) -> None:
        self._entries[conversation_id] = (info, time.monotonic())

    def evict(self, conversation_id: str) -> None:
        self._entries.pop(conversation_id, None)

    def warm(self, items: dict[str, SandboxInfo]) -> None:
        now = time.monotonic()
        for cid, info in items.items():
            self._entries[cid] = (info, now)


# ---------------------------------------------------------------------------
# Async K8s helper
# ---------------------------------------------------------------------------

class _AsyncK8sHelper:
    """Async helper for agent-sandbox CRD operations using kubernetes_asyncio."""

    def __init__(self) -> None:
        self._initialized = False
        self._init_lock = asyncio.Lock()
        self._api_client: client.ApiClient | None = None
        self._custom: client.CustomObjectsApi | None = None

    async def _ensure_initialized(self) -> None:
        if self._initialized:
            return
        async with self._init_lock:
            if self._initialized:
                return
            try:
                config.load_incluster_config()
            except config.ConfigException:
                await config.load_kube_config()
            self._api_client = client.ApiClient()
            self._custom = client.CustomObjectsApi(self._api_client)
            self._initialized = True

    async def create_sandbox_claim(
        self,
        name: str,
        template: str,
        namespace: str,
        labels: dict[str, str] | None = None,
    ) -> dict:  # type: ignore[type-arg]
        """Create a SandboxClaim. Returns the created object. Raises ApiException(409) on conflict."""
        await self._ensure_initialized()
        assert self._custom is not None
        now = datetime.now(timezone.utc).isoformat()
        manifest = {
            "apiVersion": f"{CLAIM_API_GROUP}/{CLAIM_API_VERSION}",
            "kind": "SandboxClaim",
            "metadata": {
                "name": name,
                "labels": labels or {},
                "annotations": {ANNOTATION_LAST_ACTIVITY: now},
            },
            "spec": {"sandboxTemplateRef": {"name": template}},
        }
        logger.info("Creating SandboxClaim '%s' (template=%s)", name, template)
        return await self._custom.create_namespaced_custom_object(
            group=CLAIM_API_GROUP, version=CLAIM_API_VERSION,
            namespace=namespace, plural=CLAIM_PLURAL, body=manifest,
        )

    async def get_sandbox_claim(self, name: str, namespace: str) -> dict | None:  # type: ignore[type-arg]
        """GET a SandboxClaim by name. Returns None if not found."""
        await self._ensure_initialized()
        assert self._custom is not None
        try:
            return await self._custom.get_namespaced_custom_object(
                group=CLAIM_API_GROUP, version=CLAIM_API_VERSION,
                namespace=namespace, plural=CLAIM_PLURAL, name=name,
            )
        except client.ApiException as e:
            if e.status == 404:
                return None
            raise

    async def patch_claim_annotation(self, name: str, namespace: str, annotations: dict[str, str]) -> None:
        """PATCH annotations on a SandboxClaim using merge-patch."""
        await self._ensure_initialized()
        assert self._custom is not None
        patch = {"metadata": {"annotations": annotations}}
        await self._custom.patch_namespaced_custom_object(
            group=CLAIM_API_GROUP, version=CLAIM_API_VERSION,
            namespace=namespace, plural=CLAIM_PLURAL, name=name, body=patch,
            _content_type="application/merge-patch+json",
        )

    async def list_sandbox_claims(self, namespace: str, label_selector: str) -> list:  # type: ignore[type-arg]
        """LIST SandboxClaims matching a label selector."""
        await self._ensure_initialized()
        assert self._custom is not None
        response = await self._custom.list_namespaced_custom_object(
            group=CLAIM_API_GROUP, version=CLAIM_API_VERSION,
            namespace=namespace, plural=CLAIM_PLURAL,
            label_selector=label_selector,
        )
        return response.get("items", [])

    async def resolve_sandbox_name(self, claim_name: str, namespace: str, timeout: int) -> str:
        await self._ensure_initialized()
        assert self._custom is not None
        deadline = time.monotonic() + timeout
        logger.info("Resolving sandbox name from claim '%s'...", claim_name)
        while True:
            remaining = int(deadline - time.monotonic())
            if remaining <= 0:
                raise TimeoutError(f"Could not resolve sandbox name from claim '{claim_name}' within {timeout}s")
            w = watch.Watch()
            try:
                async for event in w.stream(
                    self._custom.list_namespaced_custom_object,
                    namespace=namespace, group=CLAIM_API_GROUP,
                    version=CLAIM_API_VERSION, plural=CLAIM_PLURAL,
                    field_selector=f"metadata.name={claim_name}",
                    timeout_seconds=remaining,
                ):
                    if event is None:
                        continue
                    if event["type"] == "DELETED":
                        raise RuntimeError(f"SandboxClaim '{claim_name}' deleted while resolving")
                    if event["type"] in ("ADDED", "MODIFIED"):
                        sandbox_status = event["object"].get("status", {}).get("sandbox", {})
                        name = sandbox_status.get("name", "") or sandbox_status.get("Name", "")
                        if name:
                            logger.info("Resolved sandbox name '%s' from claim '%s'", name, claim_name)
                            return name
            finally:
                await w.close()

    async def wait_for_sandbox_ready(self, name: str, namespace: str, timeout: int) -> None:
        await self._ensure_initialized()
        assert self._custom is not None
        deadline = time.monotonic() + timeout
        logger.info("Waiting for Sandbox '%s' to become ready...", name)
        while True:
            remaining = int(deadline - time.monotonic())
            if remaining <= 0:
                raise TimeoutError(f"Sandbox '{name}' did not become ready within {timeout}s")
            w = watch.Watch()
            try:
                async for event in w.stream(
                    self._custom.list_namespaced_custom_object,
                    namespace=namespace, group=SANDBOX_API_GROUP,
                    version=SANDBOX_API_VERSION, plural=SANDBOX_PLURAL,
                    field_selector=f"metadata.name={name}",
                    timeout_seconds=remaining,
                ):
                    if event is None:
                        continue
                    if event["type"] == "DELETED":
                        raise RuntimeError(f"Sandbox '{name}' deleted before becoming ready")
                    if event["type"] in ("ADDED", "MODIFIED"):
                        conditions = event["object"].get("status", {}).get("conditions", [])
                        for c in conditions:
                            if c.get("type") == "Ready" and c.get("status") == "True":
                                logger.info("Sandbox '%s' is ready", name)
                                return
            finally:
                await w.close()

    async def get_sandbox(self, name: str, namespace: str) -> dict | None:  # type: ignore[type-arg]
        await self._ensure_initialized()
        assert self._custom is not None
        try:
            return await self._custom.get_namespaced_custom_object(
                group=SANDBOX_API_GROUP, version=SANDBOX_API_VERSION,
                namespace=namespace, plural=SANDBOX_PLURAL, name=name,
            )
        except client.ApiException as e:
            if e.status == 404:
                return None
            raise

    async def delete_sandbox_claim(self, name: str, namespace: str) -> None:
        """Delete a SandboxClaim. 404 is treated as success."""
        await self._ensure_initialized()
        assert self._custom is not None
        try:
            await self._custom.delete_namespaced_custom_object(
                group=CLAIM_API_GROUP, version=CLAIM_API_VERSION,
                namespace=namespace, plural=CLAIM_PLURAL, name=name,
            )
            logger.info("Deleted SandboxClaim '%s'", name)
        except client.ApiException as e:
            if e.status != 404:
                raise

    async def close(self) -> None:
        if self._api_client:
            await self._api_client.close()
            self._api_client = None
            self._initialized = False


# ---------------------------------------------------------------------------
# SandboxManager — K8s as source of truth, local cache for performance
# ---------------------------------------------------------------------------

class SandboxManager:
    """Manages per-conversation sandbox lifecycle with K8s-native state."""

    def __init__(self, config: SchedulerConfig) -> None:
        self._config = config
        self._k8s = _AsyncK8sHelper()
        self._cache = SandboxCache()

    def _service_fqdn(self, sandbox_name: str) -> str:
        return f"{sandbox_name}.{self._config.namespace}.svc.cluster.local"

    def _claim_name(self, conversation_id: str) -> str:
        """Deterministic claim name from conversation ID."""
        short = conversation_id[:48].lower().replace("_", "-")
        suffix = uuid.uuid5(uuid.NAMESPACE_URL, conversation_id).hex[:8]
        return f"sched-{short}-{suffix}"

    async def get_sandbox(self, conversation_id: str) -> SandboxInfo | None:
        """Look up an existing sandbox for the conversation. Returns None if not found."""
        # 1. Check local cache
        cached = self._cache.get(conversation_id)
        if cached:
            return cached

        claim_name = self._claim_name(conversation_id)
        namespace = self._config.namespace

        # 2. Check K8s — GET by deterministic name
        claim = await self._k8s.get_sandbox_claim(claim_name, namespace)
        if claim:
            info = self._info_from_claim(claim)
            if info:
                self._cache.put(conversation_id, info)
                await self._patch_last_activity(claim_name, namespace)
                return info

        return None

    async def create_sandbox(self, conversation_id: str) -> SandboxInfo:
        """Create a new sandbox for the conversation. Checks admission control."""
        claim_name = self._claim_name(conversation_id)
        namespace = self._config.namespace
        deadline = time.monotonic() + self._config.sandbox_ready_timeout

        # Admission control
        if self._config.max_active_sandboxes > 0:
            claims = await self._k8s.list_sandbox_claims(
                namespace, f"{LABEL_MANAGED_BY}={MANAGED_BY_VALUE}"
            )
            if len(claims) >= self._config.max_active_sandboxes:
                raise SandboxCapacityError(
                    f"Sandbox capacity reached ({len(claims)}/{self._config.max_active_sandboxes} active). Retry later."
                )

        labels = {
            LABEL_CONVERSATION_ID: conversation_id,
            LABEL_MANAGED_BY: MANAGED_BY_VALUE,
        }

        with tracer.start_as_current_span(
            "scheduler.sandbox.create",
            attributes={"sandbox.claim_name": claim_name, "sandbox.template": self._config.sandbox_template},
        ) as span:
            try:
                await self._k8s.create_sandbox_claim(
                    name=claim_name,
                    template=self._config.sandbox_template,
                    namespace=namespace,
                    labels=labels,
                )
            except client.ApiException as e:
                if e.status == 409:
                    logger.info("SandboxClaim '%s' already exists (conflict), using existing", claim_name)
                else:
                    span.set_status(StatusCode.ERROR, str(e))
                    span.record_exception(e)
                    raise
            except Exception as e:
                span.set_status(StatusCode.ERROR, str(e))
                span.record_exception(e)
                raise

        with tracer.start_as_current_span(
            "scheduler.sandbox.resolve_name",
            attributes={"sandbox.claim_name": claim_name},
        ) as span:
            try:
                remaining = int(deadline - time.monotonic())
                if remaining <= 0:
                    raise TimeoutError(f"Sandbox creation timed out for '{claim_name}'")
                sandbox_name = await self._k8s.resolve_sandbox_name(
                    claim_name=claim_name, namespace=namespace, timeout=remaining
                )
                span.set_attribute("sandbox.name", sandbox_name)
            except Exception as e:
                span.set_status(StatusCode.ERROR, str(e))
                span.record_exception(e)
                raise

        with tracer.start_as_current_span(
            "scheduler.sandbox.wait_ready",
            attributes={"sandbox.name": sandbox_name},
        ) as span:
            try:
                remaining = int(deadline - time.monotonic())
                if remaining <= 0:
                    raise TimeoutError(f"Sandbox creation timed out waiting for '{sandbox_name}' to become ready")
                await self._k8s.wait_for_sandbox_ready(name=sandbox_name, namespace=namespace, timeout=remaining)
            except Exception as e:
                span.set_status(StatusCode.ERROR, str(e))
                span.record_exception(e)
                raise

        service_fqdn = self._service_fqdn(sandbox_name)
        info = SandboxInfo(claim_name=claim_name, sandbox_name=sandbox_name, service_fqdn=service_fqdn)
        self._cache.put(conversation_id, info)
        logger.info("Sandbox ready: conversation=%s sandbox=%s fqdn=%s", conversation_id, sandbox_name, service_fqdn)

        return info

    async def update_last_activity(self, conversation_id: str) -> None:
        """PATCH last-activity annotation on the claim."""
        claim_name = self._claim_name(conversation_id)
        await self._patch_last_activity(claim_name, self._config.namespace)

    async def recover_sandbox(self, conversation_id: str) -> SandboxInfo:
        """Attempt to recover a sandbox. Checks health before deleting."""
        self._cache.evict(conversation_id)
        claim_name = self._claim_name(conversation_id)
        namespace = self._config.namespace

        # Check if claim and sandbox still exist and are healthy
        claim = await self._k8s.get_sandbox_claim(claim_name, namespace)
        if claim:
            info = self._info_from_claim(claim)
            if info:
                sandbox = await self._k8s.get_sandbox(name=info.sandbox_name, namespace=namespace)
                if sandbox and self._is_sandbox_ready(sandbox):
                    # Sandbox is actually healthy — cache was stale
                    self._cache.put(conversation_id, info)
                    return info

        # Sandbox is genuinely gone — delete stale claim and recreate
        await self._k8s.delete_sandbox_claim(claim_name, namespace)
        return await self.create_sandbox(conversation_id)

    async def warm_cache(self) -> None:
        """Warm local cache from existing SandboxClaims on startup."""
        namespace = self._config.namespace
        logger.info("Warming cache from SandboxClaims in namespace '%s'", namespace)

        try:
            claims = await self._k8s.list_sandbox_claims(
                namespace, f"{LABEL_MANAGED_BY}={MANAGED_BY_VALUE}"
            )
        except Exception:
            logger.exception("Failed to list SandboxClaims during cache warm")
            return

        items: dict[str, SandboxInfo] = {}
        for item in claims:
            metadata = item.get("metadata", {})
            item_labels = metadata.get("labels", {})
            claim_name = metadata.get("name", "")
            conversation_id = item_labels.get(LABEL_CONVERSATION_ID, "")

            if not conversation_id or not claim_name:
                continue

            sandbox_status = item.get("status", {}).get("sandbox", {})
            sandbox_name = sandbox_status.get("name", "") or sandbox_status.get("Name", "")

            if not sandbox_name:
                logger.warning("Orphaned claim '%s' has no sandbox name, deleting", claim_name)
                await self._k8s.delete_sandbox_claim(claim_name, namespace)
                continue

            sandbox = await self._k8s.get_sandbox(name=sandbox_name, namespace=namespace)
            if not sandbox or not self._is_sandbox_ready(sandbox):
                logger.warning("Orphaned claim '%s' (sandbox '%s' not ready), deleting", claim_name, sandbox_name)
                await self._k8s.delete_sandbox_claim(claim_name, namespace)
                continue

            items[conversation_id] = SandboxInfo(
                claim_name=claim_name,
                sandbox_name=sandbox_name,
                service_fqdn=self._service_fqdn(sandbox_name),
            )
            logger.info("Cached mapping: conversation=%s -> sandbox=%s", conversation_id, sandbox_name)

        self._cache.warm(items)
        logger.info("Cache warm complete: %d active conversations", len(items))

    async def run_reaper(self) -> None:
        """Background task that reaps idle sessions by reading claim annotations."""
        while True:
            try:
                await asyncio.sleep(30)
                await self._reap_once()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Reaper error")

    async def _reap_once(self) -> None:
        """Single reaper cycle: list claims, evict+delete expired ones."""
        namespace = self._config.namespace
        ttl = self._config.session_idle_ttl
        now = datetime.now(timezone.utc)

        claims = await self._k8s.list_sandbox_claims(
            namespace, f"{LABEL_MANAGED_BY}={MANAGED_BY_VALUE}"
        )

        for item in claims:
            metadata = item.get("metadata", {})
            claim_name = metadata.get("name", "")
            conversation_id = metadata.get("labels", {}).get(LABEL_CONVERSATION_ID, "")
            annotations = metadata.get("annotations", {})

            last_activity_str = annotations.get(ANNOTATION_LAST_ACTIVITY, "")
            if last_activity_str:
                try:
                    last_activity = datetime.fromisoformat(last_activity_str)
                    idle_seconds = (now - last_activity).total_seconds()
                except ValueError:
                    idle_seconds = ttl + 1  # treat unparseable as expired
            else:
                # No annotation — use creation timestamp as fallback
                created = metadata.get("creationTimestamp", "")
                try:
                    created_dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                    idle_seconds = (now - created_dt).total_seconds()
                except (ValueError, AttributeError):
                    idle_seconds = ttl + 1

            if idle_seconds > ttl:
                logger.info("Reaping idle session: conversation=%s claim=%s idle=%.0fs", conversation_id, claim_name, idle_seconds)
                # Evict cache before deleting claim to avoid routing to a dead sandbox
                if conversation_id:
                    self._cache.evict(conversation_id)
                if self._config.shutdown_policy == "Delete":
                    await self._k8s.delete_sandbox_claim(claim_name, namespace)

    async def close(self) -> None:
        await self._k8s.close()

    def _info_from_claim(self, claim: dict) -> SandboxInfo | None:  # type: ignore[type-arg]
        """Extract SandboxInfo from a claim object, or None if sandbox isn't ready."""
        sandbox_status = claim.get("status", {}).get("sandbox", {})
        sandbox_name = sandbox_status.get("name", "") or sandbox_status.get("Name", "")
        if not sandbox_name:
            return None
        claim_name = claim.get("metadata", {}).get("name", "")
        return SandboxInfo(
            claim_name=claim_name,
            sandbox_name=sandbox_name,
            service_fqdn=self._service_fqdn(sandbox_name),
        )

    async def _patch_last_activity(self, claim_name: str, namespace: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        try:
            await self._k8s.patch_claim_annotation(claim_name, namespace, {ANNOTATION_LAST_ACTIVITY: now})
        except Exception:
            logger.warning("Failed to patch last-activity on '%s'", claim_name, exc_info=True)

    @staticmethod
    def _is_sandbox_ready(sandbox: dict) -> bool:  # type: ignore[type-arg]
        conditions = sandbox.get("status", {}).get("conditions", [])
        return any(c.get("type") == "Ready" and c.get("status") == "True" for c in conditions)
