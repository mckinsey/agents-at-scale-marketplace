"""Sandbox controller - manages Sandbox CR lifecycle."""

import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Optional

import kopf
from kubernetes import client
from kubernetes.client.rest import ApiException

from k8s.manager import KubernetesManager, DEFAULT_IMAGE, DEFAULT_TTL_MINUTES

logger = logging.getLogger(__name__)

# Singleton manager instance
_manager: Optional[KubernetesManager] = None


def get_manager() -> KubernetesManager:
    """Get or create the Kubernetes manager singleton."""
    global _manager
    if _manager is None:
        _manager = KubernetesManager()
    return _manager


@kopf.on.create("ark.mckinsey.com", "v1alpha1", "sandboxes")
async def sandbox_created(
    spec: Dict[str, Any],
    name: str,
    namespace: str,
    uid: str,
    patch: kopf.Patch,
    **kwargs,
) -> Dict[str, Any]:
    """Handle Sandbox creation - create pod with PVC mount.

    Args:
        spec: Sandbox spec
        name: Sandbox name
        namespace: Kubernetes namespace
        uid: Sandbox UID
        patch: Patch object for status updates

    Returns:
        Dict with creation result
    """
    logger.info(f"Creating sandbox {name} in namespace {namespace}")

    manager = get_manager()

    # Get spec values with defaults
    image = spec.get("image") or DEFAULT_IMAGE
    ttl_minutes = spec.get("ttlMinutes") or DEFAULT_TTL_MINUTES
    pvc_name = spec.get("pvcName")

    # Resolve template if referenced
    template_ref = spec.get("templateRef")
    if template_ref:
        try:
            template = manager.custom_api.get_namespaced_custom_object(
                group="ark.mckinsey.com",
                version="v1alpha1",
                namespace=namespace,
                plural="sandboxtemplates",
                name=template_ref["name"],
            )
            template_spec = template.get("spec", {})
            image = template_spec.get("image", image)
            ttl_minutes = template_spec.get("ttlMinutes", ttl_minutes)
            logger.info(f"Resolved template {template_ref['name']}: image={image}")
        except ApiException as e:
            if e.status == 404:
                logger.warning(f"Template {template_ref['name']} not found, using defaults")
            else:
                raise

    # Create owner reference for garbage collection
    owner_reference = {
        "apiVersion": "ark.mckinsey.com/v1alpha1",
        "kind": "Sandbox",
        "name": name,
        "uid": uid,
    }

    # Create the pod
    try:
        pod = await manager.create_pod(
            name=name,
            namespace=namespace,
            image=image,
            ttl_minutes=ttl_minutes,
            pvc_name=pvc_name,
            owner_reference=owner_reference,
        )

        # Calculate expiry time
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=ttl_minutes)

        # Update status
        patch.status["phase"] = "Pending"
        patch.status["podName"] = pod.metadata.name
        patch.status["expiresAt"] = expires_at.isoformat()

        logger.info(f"Created pod {pod.metadata.name} for sandbox {name}")

        return {"pod_name": pod.metadata.name}

    except ApiException as e:
        if e.status == 409:
            # Pod already exists - this is fine, just update status to track it
            logger.info(f"Pod {name} already exists for sandbox {name}, using existing pod")
            expires_at = datetime.now(timezone.utc) + timedelta(minutes=ttl_minutes)
            patch.status["phase"] = "Pending"
            patch.status["podName"] = name
            patch.status["expiresAt"] = expires_at.isoformat()
            return {"pod_name": name}
        else:
            logger.error(f"Failed to create pod for sandbox {name}: {e}")
            patch.status["phase"] = "Terminated"
            patch.status["message"] = str(e)
            raise kopf.PermanentError(f"Failed to create pod: {e}")
    except Exception as e:
        logger.error(f"Failed to create pod for sandbox {name}: {e}")
        patch.status["phase"] = "Terminated"
        patch.status["message"] = str(e)
        raise kopf.PermanentError(f"Failed to create pod: {e}")


@kopf.on.update("ark.mckinsey.com", "v1alpha1", "sandboxes", field="spec.pvcName")
async def sandbox_pvc_updated(
    spec: Dict[str, Any],
    status: Dict[str, Any],
    name: str,
    namespace: str,
    old: Optional[str],
    new: Optional[str],
    patch: kopf.Patch,
    **kwargs,
) -> None:
    """Handle PVC attachment to existing sandbox.

    This is used when claiming a sandbox from a pool and attaching a PVC.
    """
    if old == new:
        return

    logger.info(f"PVC changed for sandbox {name}: {old} -> {new}")

    if new and status.get("phase") == "Running":
        # Need to recreate pod with PVC mount
        # For now, log a warning - full implementation would recreate the pod
        logger.warning(
            f"PVC attachment to running sandbox {name} requires pod recreation. "
            "Consider creating a new sandbox with the PVC instead."
        )


@kopf.timer("ark.mckinsey.com", "v1alpha1", "sandboxes", interval=30.0)
async def sandbox_timer(
    spec: Dict[str, Any],
    status: Dict[str, Any],
    name: str,
    namespace: str,
    patch: kopf.Patch,
    **kwargs,
) -> None:
    """Periodic check for sandbox state and TTL.

    - Updates phase based on pod status
    - Checks TTL expiry
    """
    manager = get_manager()
    current_phase = status.get("phase", "Unknown")
    pod_name = status.get("podName")

    if not pod_name:
        return

    # Check pod status
    try:
        pod_phase = await manager.get_pod_status(pod_name, namespace)

        if pod_phase is None:
            # Pod was deleted
            if current_phase != "Terminated":
                patch.status["phase"] = "Terminated"
                patch.status["message"] = "Pod was deleted"
            return

        # Update phase based on pod status
        if pod_phase == "Running" and current_phase == "Pending":
            # Pod is now running
            pod_ip = await manager.get_pod_ip(pod_name, namespace)
            patch.status["phase"] = "Running"
            patch.status["podIP"] = pod_ip
            patch.status["startedAt"] = datetime.now(timezone.utc).isoformat()
            logger.info(f"Sandbox {name} is now running (pod IP: {pod_ip})")

        elif pod_phase in ("Failed", "Succeeded"):
            # Pod terminated
            patch.status["phase"] = "Terminated"
            patch.status["message"] = f"Pod phase: {pod_phase}"

    except Exception as e:
        logger.error(f"Error checking pod status for sandbox {name}: {e}")

    # Check TTL expiry
    if current_phase == "Running":
        expires_at_str = status.get("expiresAt")
        if expires_at_str:
            try:
                expires_at = datetime.fromisoformat(expires_at_str.replace("Z", "+00:00"))
                if datetime.now(timezone.utc) > expires_at:
                    logger.info(f"Sandbox {name} has expired, terminating")
                    patch.status["phase"] = "Terminated"
                    patch.status["message"] = "TTL expired"
            except ValueError as e:
                logger.error(f"Failed to parse expiresAt for sandbox {name}: {e}")


@kopf.on.field("ark.mckinsey.com", "v1alpha1", "sandboxes", field="status.phase")
async def sandbox_phase_changed(
    old: Optional[str],
    new: Optional[str],
    name: str,
    namespace: str,
    status: Dict[str, Any],
    **kwargs,
) -> None:
    """React to phase changes.

    When phase changes to Terminated, clean up the pod.
    """
    if old == new:
        return

    logger.info(f"Sandbox {name} phase changed: {old} -> {new}")

    if new == "Terminated":
        manager = get_manager()
        pod_name = status.get("podName")

        if pod_name:
            logger.info(f"Deleting pod {pod_name} for terminated sandbox {name}")
            try:
                await manager.delete_pod(pod_name, namespace)
            except Exception as e:
                logger.error(f"Failed to delete pod {pod_name}: {e}")


@kopf.on.delete("ark.mckinsey.com", "v1alpha1", "sandboxes")
async def sandbox_deleted(
    name: str,
    namespace: str,
    status: Dict[str, Any],
    **kwargs,
) -> None:
    """Handle Sandbox deletion - ensure pod is cleaned up.

    Note: Pod should be garbage collected via owner reference,
    but we clean up explicitly just in case.
    """
    logger.info(f"Sandbox {name} deleted")

    manager = get_manager()
    pod_name = status.get("podName")

    if pod_name:
        try:
            await manager.delete_pod(pod_name, namespace)
        except Exception as e:
            logger.warning(f"Failed to delete pod {pod_name} during sandbox deletion: {e}")

