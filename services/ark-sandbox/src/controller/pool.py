"""SandboxPool controller - manages warm pool of sandboxes."""

import logging
from typing import Any, Dict, List, Optional

import kopf
from kubernetes.client.rest import ApiException

from k8s.manager import KubernetesManager

logger = logging.getLogger(__name__)

# Singleton manager instance
_manager: Optional[KubernetesManager] = None


def get_manager() -> KubernetesManager:
    """Get or create the Kubernetes manager singleton."""
    global _manager
    if _manager is None:
        _manager = KubernetesManager()
    return _manager


async def get_pool_sandboxes(
    manager: KubernetesManager,
    pool_name: str,
    namespace: str,
) -> List[Dict[str, Any]]:
    """Get all sandboxes belonging to a pool.

    Args:
        manager: Kubernetes manager
        pool_name: Pool name
        namespace: Kubernetes namespace

    Returns:
        List of sandbox dicts
    """
    try:
        result = manager.custom_api.list_namespaced_custom_object(
            group="ark.mckinsey.com",
            version="v1alpha1",
            namespace=namespace,
            plural="sandboxes",
            label_selector=f"ark.mckinsey.com/pool={pool_name}",
        )
        return result.get("items", [])
    except ApiException as e:
        logger.error(f"Failed to list pool sandboxes: {e}")
        return []


async def create_warm_sandbox(
    manager: KubernetesManager,
    pool_name: str,
    namespace: str,
    template_ref: Dict[str, str],
) -> Optional[str]:
    """Create a warm sandbox for the pool.

    Args:
        manager: Kubernetes manager
        pool_name: Pool name
        namespace: Kubernetes namespace
        template_ref: Reference to SandboxTemplate

    Returns:
        Created sandbox name or None
    """
    template_name = template_ref.get("name")
    if not template_name:
        logger.error(f"Pool {pool_name} has no templateRef.name")
        return None

    # Get template spec
    try:
        template = manager.custom_api.get_namespaced_custom_object(
            group="ark.mckinsey.com",
            version="v1alpha1",
            namespace=namespace,
            plural="sandboxtemplates",
            name=template_name,
        )
        template_spec = template.get("spec", {})
    except ApiException as e:
        logger.error(f"Failed to get template {template_name}: {e}")
        return None

    # Create sandbox with pool label
    import uuid
    sandbox_name = f"{pool_name}-{uuid.uuid4().hex[:8]}"

    sandbox_cr = {
        "apiVersion": "ark.mckinsey.com/v1alpha1",
        "kind": "Sandbox",
        "metadata": {
            "name": sandbox_name,
            "namespace": namespace,
            "labels": {
                "ark.mckinsey.com/pool": pool_name,
                "ark.mckinsey.com/claimed": "false",
            },
        },
        "spec": {
            "image": template_spec.get("image", "python:3.12-slim"),
            "ttlMinutes": template_spec.get("ttlMinutes", 120),
            "resources": template_spec.get("resources", {}),
        },
    }

    try:
        manager.custom_api.create_namespaced_custom_object(
            group="ark.mckinsey.com",
            version="v1alpha1",
            namespace=namespace,
            plural="sandboxes",
            body=sandbox_cr,
        )
        logger.info(f"Created warm sandbox {sandbox_name} for pool {pool_name}")
        return sandbox_name
    except ApiException as e:
        logger.error(f"Failed to create warm sandbox: {e}")
        return None


def count_sandboxes_by_state(sandboxes: List[Dict[str, Any]]) -> Dict[str, int]:
    """Count sandboxes by claimed/unclaimed state.

    Args:
        sandboxes: List of sandbox dicts

    Returns:
        Dict with ready_count and claimed_count
    """
    ready_count = 0
    claimed_count = 0

    for sandbox in sandboxes:
        labels = sandbox.get("metadata", {}).get("labels", {})
        status = sandbox.get("status", {})
        phase = status.get("phase", "Unknown")

        is_claimed = labels.get("ark.mckinsey.com/claimed") == "true"

        if is_claimed:
            claimed_count += 1
        elif phase == "Running":
            ready_count += 1

    return {
        "ready_count": ready_count,
        "claimed_count": claimed_count,
    }


@kopf.on.create("ark.mckinsey.com", "v1alpha1", "sandboxpools")
async def pool_created(
    spec: Dict[str, Any],
    name: str,
    namespace: str,
    patch: kopf.Patch,
    **kwargs,
) -> Dict[str, Any]:
    """Handle SandboxPool creation - initialize warm pool.

    Args:
        spec: Pool spec
        name: Pool name
        namespace: Kubernetes namespace
        patch: Patch object for status updates

    Returns:
        Dict with creation result
    """
    logger.info(f"Creating sandbox pool {name} in namespace {namespace}")

    manager = get_manager()

    min_size = spec.get("minSize", 0)
    template_ref = spec.get("templateRef", {})

    if not template_ref.get("name"):
        raise kopf.PermanentError("Pool must have templateRef.name")

    # Create initial warm sandboxes
    created = []
    for i in range(min_size):
        sandbox_name = await create_warm_sandbox(manager, name, namespace, template_ref)
        if sandbox_name:
            created.append(sandbox_name)

    # Update status
    patch.status["readyCount"] = 0  # Will be updated by timer once pods are running
    patch.status["claimedCount"] = 0
    patch.status["sandboxes"] = created

    logger.info(f"Initialized pool {name} with {len(created)} sandboxes")

    return {"created": len(created)}


@kopf.timer("ark.mckinsey.com", "v1alpha1", "sandboxpools", interval=30.0)
async def pool_timer(
    spec: Dict[str, Any],
    status: Dict[str, Any],
    name: str,
    namespace: str,
    patch: kopf.Patch,
    **kwargs,
) -> None:
    """Periodic check to maintain pool size.

    - Counts ready/claimed sandboxes
    - Creates new sandboxes if below minSize
    - Updates status
    """
    manager = get_manager()

    min_size = spec.get("minSize", 0)
    max_size = spec.get("maxSize", min_size * 2) if spec.get("maxSize") else min_size * 2
    template_ref = spec.get("templateRef", {})

    # Get current pool sandboxes
    sandboxes = await get_pool_sandboxes(manager, name, namespace)

    # Count by state
    counts = count_sandboxes_by_state(sandboxes)
    ready_count = counts["ready_count"]
    claimed_count = counts["claimed_count"]
    total_count = len(sandboxes)

    # Update status
    patch.status["readyCount"] = ready_count
    patch.status["claimedCount"] = claimed_count
    patch.status["sandboxes"] = [s["metadata"]["name"] for s in sandboxes]

    # Check if we need to create more warm sandboxes
    if ready_count < min_size and total_count < max_size:
        needed = min(min_size - ready_count, max_size - total_count)
        logger.info(f"Pool {name}: ready={ready_count}, need={needed} more warm sandboxes")

        for _ in range(needed):
            await create_warm_sandbox(manager, name, namespace, template_ref)


@kopf.on.delete("ark.mckinsey.com", "v1alpha1", "sandboxpools")
async def pool_deleted(
    name: str,
    namespace: str,
    status: Dict[str, Any],
    **kwargs,
) -> None:
    """Handle SandboxPool deletion - clean up all pool sandboxes.

    Args:
        name: Pool name
        namespace: Kubernetes namespace
        status: Pool status
    """
    logger.info(f"Deleting sandbox pool {name}")

    manager = get_manager()

    # Delete all sandboxes in the pool
    sandboxes = await get_pool_sandboxes(manager, name, namespace)

    for sandbox in sandboxes:
        sandbox_name = sandbox["metadata"]["name"]
        try:
            manager.custom_api.delete_namespaced_custom_object(
                group="ark.mckinsey.com",
                version="v1alpha1",
                namespace=namespace,
                plural="sandboxes",
                name=sandbox_name,
            )
            logger.info(f"Deleted pool sandbox {sandbox_name}")
        except ApiException as e:
            if e.status != 404:
                logger.error(f"Failed to delete sandbox {sandbox_name}: {e}")


@kopf.on.event("ark.mckinsey.com", "v1alpha1", "sandboxes")
async def sandbox_event(
    event: Dict[str, Any],
    name: str,
    namespace: str,
    labels: Dict[str, str],
    **kwargs,
) -> None:
    """Watch sandbox events to trigger pool replenishment.

    When a sandbox is claimed or deleted, check if pool needs replenishment.
    """
    pool_name = labels.get("ark.mckinsey.com/pool")
    if not pool_name:
        return

    event_type = event.get("type")

    # Only react to relevant events
    if event_type not in ("MODIFIED", "DELETED"):
        return

    # Check if sandbox was just claimed
    if event_type == "MODIFIED":
        obj = event.get("object", {})
        claimed = obj.get("metadata", {}).get("labels", {}).get("ark.mckinsey.com/claimed")
        if claimed != "true":
            return

    logger.debug(f"Sandbox {name} event ({event_type}) may require pool {pool_name} replenishment")

    # Pool replenishment is handled by the pool timer
    # This event handler is mainly for logging/debugging

