"""Sandbox lifecycle management: creation, routing, reaping, and recovery."""

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field

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


@dataclass
class SandboxInfo:
    """Conversation-to-sandbox mapping entry."""

    claim_name: str
    sandbox_name: str
    service_fqdn: str
    last_activity: float = field(default_factory=time.monotonic)


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
    ) -> None:
        await self._ensure_initialized()
        assert self._custom is not None
        manifest = {
            "apiVersion": f"{CLAIM_API_GROUP}/{CLAIM_API_VERSION}",
            "kind": "SandboxClaim",
            "metadata": {"name": name, "labels": labels or {}},
            "spec": {"sandboxTemplateRef": {"name": template}},
        }
        logger.info("Creating SandboxClaim '%s' (template=%s)", name, template)
        await self._custom.create_namespaced_custom_object(
            group=CLAIM_API_GROUP, version=CLAIM_API_VERSION,
            namespace=namespace, plural=CLAIM_PLURAL, body=manifest,
        )

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


class SandboxManager:
    """Manages per-conversation sandbox lifecycle."""

    def __init__(self, config: SchedulerConfig) -> None:
        self._config = config
        self._k8s = _AsyncK8sHelper()
        self._routing_table: dict[str, SandboxInfo] = {}
        self._locks: dict[str, asyncio.Lock] = {}
        self._global_lock = asyncio.Lock()

    def _service_fqdn(self, sandbox_name: str) -> str:
        """Derive the service FQDN for a sandbox."""
        return f"{sandbox_name}.{self._config.namespace}.svc.cluster.local"

    def _claim_name(self, conversation_id: str) -> str:
        """Generate a deterministic claim name from conversation ID."""
        short = conversation_id[:48].lower().replace("_", "-")
        suffix = uuid.uuid5(uuid.NAMESPACE_URL, conversation_id).hex[:8]
        return f"sched-{short}-{suffix}"

    async def _get_lock(self, conversation_id: str) -> asyncio.Lock:
        """Get or create a per-conversation lock."""
        async with self._global_lock:
            if conversation_id not in self._locks:
                self._locks[conversation_id] = asyncio.Lock()
            return self._locks[conversation_id]

    async def ensure_sandbox(self, conversation_id: str) -> tuple[SandboxInfo, bool]:
        """Get or create a sandbox for the given conversation. Returns (info, is_new)."""
        lock = await self._get_lock(conversation_id)
        async with lock:
            existing = self._routing_table.get(conversation_id)
            if existing:
                existing.last_activity = time.monotonic()
                return existing, False

            info = await self._create_sandbox(conversation_id)
            self._routing_table[conversation_id] = info
            return info, True

    async def _create_sandbox(self, conversation_id: str) -> SandboxInfo:
        """Create a new sandbox for a conversation."""
        claim_name = self._claim_name(conversation_id)
        namespace = self._config.namespace
        timeout = self._config.sandbox_ready_timeout

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
            except Exception as e:
                span.set_status(StatusCode.ERROR, str(e))
                span.record_exception(e)
                raise

        with tracer.start_as_current_span(
            "scheduler.sandbox.resolve_name",
            attributes={"sandbox.claim_name": claim_name},
        ) as span:
            try:
                sandbox_name = await self._k8s.resolve_sandbox_name(
                    claim_name=claim_name, namespace=namespace, timeout=timeout
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
                await self._k8s.wait_for_sandbox_ready(name=sandbox_name, namespace=namespace, timeout=timeout)
            except Exception as e:
                span.set_status(StatusCode.ERROR, str(e))
                span.record_exception(e)
                raise

        service_fqdn = self._service_fqdn(sandbox_name)
        logger.info("Sandbox ready: conversation=%s sandbox=%s fqdn=%s", conversation_id, sandbox_name, service_fqdn)

        return SandboxInfo(
            claim_name=claim_name,
            sandbox_name=sandbox_name,
            service_fqdn=service_fqdn,
        )

    def touch(self, conversation_id: str) -> None:
        """Update last activity timestamp for a conversation."""
        info = self._routing_table.get(conversation_id)
        if info:
            info.last_activity = time.monotonic()

    def add_alias(self, alias_id: str, original_id: str) -> None:
        """Register an alias so a different context_id routes to the same sandbox.

        This handles the case where the first query has no conversationId,
        so the scheduler generates a routing key, but the executor's response
        contains a contextId that the controller writes to subsequent queries.
        """
        info = self._routing_table.get(original_id)
        if info and alias_id not in self._routing_table:
            self._routing_table[alias_id] = info
            logger.info("Registered alias: %s -> sandbox %s (original key: %s)", alias_id, info.sandbox_name, original_id)

    async def remove_sandbox(self, conversation_id: str) -> None:
        """Remove a sandbox mapping and optionally delete the claim."""
        info = self._routing_table.pop(conversation_id, None)
        self._locks.pop(conversation_id, None)
        if info and self._config.shutdown_policy == "Delete":
            try:
                await self._k8s.delete_sandbox_claim(name=info.claim_name, namespace=self._config.namespace)
            except Exception:
                logger.exception("Failed to delete SandboxClaim %s", info.claim_name)

    async def recover_sandbox(self, conversation_id: str) -> tuple[SandboxInfo, bool]:
        """Remove stale mapping and create a new sandbox."""
        self._routing_table.pop(conversation_id, None)
        self._locks.pop(conversation_id, None)
        return await self.ensure_sandbox(conversation_id)

    async def rebuild_map(self) -> None:
        """Rebuild routing table from existing SandboxClaims on startup."""
        namespace = self._config.namespace
        logger.info("Rebuilding conversation map from SandboxClaims in namespace '%s'", namespace)

        try:
            try:
                config.load_incluster_config()
            except config.ConfigException:
                await config.load_kube_config()

            api = client.CustomObjectsApi()
            response = await api.list_namespaced_custom_object(
                group=CLAIM_API_GROUP,
                version=CLAIM_API_VERSION,
                namespace=namespace,
                plural=CLAIM_PLURAL,
                label_selector=f"{LABEL_MANAGED_BY}={MANAGED_BY_VALUE}",
            )
        except Exception:
            logger.exception("Failed to list SandboxClaims during rebuild")
            return

        for item in response.get("items", []):
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
                await self._safe_delete_claim(claim_name, namespace)
                continue

            sandbox = await self._k8s.get_sandbox(name=sandbox_name, namespace=namespace)
            if not sandbox or not self._is_sandbox_ready(sandbox):
                logger.warning("Orphaned claim '%s' (sandbox '%s' not ready), deleting", claim_name, sandbox_name)
                await self._safe_delete_claim(claim_name, namespace)
                continue

            service_fqdn = self._service_fqdn(sandbox_name)
            self._routing_table[conversation_id] = SandboxInfo(
                claim_name=claim_name,
                sandbox_name=sandbox_name,
                service_fqdn=service_fqdn,
            )
            logger.info("Restored mapping: conversation=%s -> sandbox=%s", conversation_id, sandbox_name)

        logger.info("Rebuild complete: %d active conversations", len(self._routing_table))

    async def run_reaper(self) -> None:
        """Background task that reaps idle sessions periodically."""
        while True:
            try:
                await asyncio.sleep(30)
                now = time.monotonic()
                ttl = self._config.session_idle_ttl
                expired = [
                    cid
                    for cid, info in self._routing_table.items()
                    if (now - info.last_activity) > ttl
                ]
                for cid in expired:
                    logger.info("Reaping idle session: conversation=%s", cid)
                    await self.remove_sandbox(cid)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Reaper error")

    async def close(self) -> None:
        """Clean up resources."""
        await self._k8s.close()

    @staticmethod
    def _is_sandbox_ready(sandbox: dict) -> bool:  # type: ignore[type-arg]
        """Check if a sandbox has a Ready condition."""
        conditions = sandbox.get("status", {}).get("conditions", [])
        return any(c.get("type") == "Ready" and c.get("status") == "True" for c in conditions)

    async def _safe_delete_claim(self, name: str, namespace: str) -> None:
        """Delete a claim, swallowing errors."""
        try:
            await self._k8s.delete_sandbox_claim(name=name, namespace=namespace)
        except Exception:
            logger.exception("Failed to delete orphaned claim '%s'", name)
