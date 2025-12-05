"""Kubernetes manager for sandbox pod and CR operations."""

import os
import uuid
import logging
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from kubernetes import client, config
from kubernetes.client.rest import ApiException
from kubernetes.stream import stream

logger = logging.getLogger(__name__)

DEFAULT_NAMESPACE = os.getenv("DEFAULT_NAMESPACE", "default")
DEFAULT_IMAGE = os.getenv("DEFAULT_IMAGE", "python:3.12-slim")
DEFAULT_TTL_MINUTES = int(os.getenv("DEFAULT_TTL_MINUTES", "120"))
POD_READY_TIMEOUT_SECONDS = int(os.getenv("POD_READY_TIMEOUT_SECONDS", "60"))

# CRD group and version
CRD_GROUP = "ark.mckinsey.com"
CRD_VERSION = "v1alpha1"


class KubernetesManager:
    """Manages Kubernetes sandbox pods and CRs."""

    def __init__(self):
        """Initialize Kubernetes client."""
        try:
            config.load_incluster_config()
            logger.info("Loaded in-cluster Kubernetes configuration")
        except config.ConfigException:
            try:
                config.load_kube_config()
                logger.info("Loaded kubeconfig for local development")
            except config.ConfigException as e:
                logger.error(f"Failed to load Kubernetes configuration: {e}")
                raise

        self.core_v1 = client.CoreV1Api()
        self.custom_api = client.CustomObjectsApi()

    def _generate_sandbox_id(self) -> str:
        """Generate unique sandbox identifier."""
        return f"sandbox-{uuid.uuid4().hex[:12]}"

    def _get_timestamp_iso(self) -> str:
        """Get current timestamp in ISO format."""
        return datetime.now(timezone.utc).isoformat()

    # =========================================================================
    # Sandbox CR Operations
    # =========================================================================

    async def create_sandbox_cr(
        self,
        image: Optional[str] = None,
        namespace: Optional[str] = None,
        ttl_minutes: Optional[int] = None,
        pvc_name: Optional[str] = None,
        resources: Optional[Dict[str, Any]] = None,
        name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a new Sandbox custom resource.

        Args:
            image: Container image to use
            namespace: Kubernetes namespace
            ttl_minutes: Time-to-live in minutes
            pvc_name: Optional PVC name to mount at /shared
            resources: Optional resource limits/requests
            name: Optional name (will generate if not provided)

        Returns:
            Dict with sandbox CR details
        """
        namespace = namespace or DEFAULT_NAMESPACE
        sandbox_name = name or self._generate_sandbox_id()

        sandbox_spec = {
            "image": image or DEFAULT_IMAGE,
            "ttlMinutes": ttl_minutes or DEFAULT_TTL_MINUTES,
        }

        if pvc_name:
            sandbox_spec["pvcName"] = pvc_name

        if resources:
            sandbox_spec["resources"] = resources

        sandbox_cr = {
            "apiVersion": f"{CRD_GROUP}/{CRD_VERSION}",
            "kind": "Sandbox",
            "metadata": {
                "name": sandbox_name,
                "namespace": namespace,
            },
            "spec": sandbox_spec,
        }

        logger.info(f"Creating Sandbox CR {sandbox_name} in namespace {namespace}")

        try:
            result = self.custom_api.create_namespaced_custom_object(
                group=CRD_GROUP,
                version=CRD_VERSION,
                namespace=namespace,
                plural="sandboxes",
                body=sandbox_cr,
            )

            return {
                "name": result["metadata"]["name"],
                "namespace": result["metadata"]["namespace"],
                "image": sandbox_spec["image"],
                "ttlMinutes": sandbox_spec["ttlMinutes"],
                "pvcName": pvc_name,
            }

        except ApiException as e:
            logger.error(f"Failed to create Sandbox CR: {e}")
            raise Exception(f"Failed to create sandbox: {e.reason}")

    async def get_sandbox_cr(
        self, name: str, namespace: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get a Sandbox custom resource.

        Args:
            name: Sandbox name
            namespace: Kubernetes namespace

        Returns:
            Dict with sandbox details
        """
        namespace = namespace or DEFAULT_NAMESPACE

        try:
            result = self.custom_api.get_namespaced_custom_object(
                group=CRD_GROUP,
                version=CRD_VERSION,
                namespace=namespace,
                plural="sandboxes",
                name=name,
            )

            spec = result.get("spec", {})
            status = result.get("status", {})

            return {
                "name": result["metadata"]["name"],
                "namespace": result["metadata"]["namespace"],
                "phase": status.get("phase", "Unknown"),
                "podName": status.get("podName"),
                "podIP": status.get("podIP"),
                "image": spec.get("image"),
                "ttlMinutes": spec.get("ttlMinutes"),
                "pvcName": spec.get("pvcName"),
                "startedAt": status.get("startedAt"),
                "expiresAt": status.get("expiresAt"),
            }

        except ApiException as e:
            if e.status == 404:
                raise Exception(f"Sandbox {name} not found in namespace {namespace}")
            logger.error(f"Failed to get Sandbox CR: {e}")
            raise Exception(f"Failed to get sandbox: {e.reason}")

    async def list_sandbox_crs(
        self, namespace: Optional[str] = None, pool_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List Sandbox custom resources.

        Args:
            namespace: Kubernetes namespace (None for all namespaces)
            pool_name: Optional pool name to filter by

        Returns:
            List of sandbox info dicts
        """
        label_selector = ""
        if pool_name:
            label_selector = f"ark.mckinsey.com/pool={pool_name}"

        try:
            if namespace:
                result = self.custom_api.list_namespaced_custom_object(
                    group=CRD_GROUP,
                    version=CRD_VERSION,
                    namespace=namespace,
                    plural="sandboxes",
                    label_selector=label_selector,
                )
            else:
                result = self.custom_api.list_cluster_custom_object(
                    group=CRD_GROUP,
                    version=CRD_VERSION,
                    plural="sandboxes",
                    label_selector=label_selector,
                )

            sandboxes = []
            for item in result.get("items", []):
                spec = item.get("spec", {})
                status = item.get("status", {})
                sandboxes.append({
                    "name": item["metadata"]["name"],
                    "namespace": item["metadata"]["namespace"],
                    "phase": status.get("phase", "Unknown"),
                    "image": spec.get("image"),
                    "ttlMinutes": spec.get("ttlMinutes"),
                    "startedAt": status.get("startedAt"),
                })

            return sandboxes

        except ApiException as e:
            logger.error(f"Failed to list Sandbox CRs: {e}")
            raise Exception(f"Failed to list sandboxes: {e.reason}")

    async def delete_sandbox_cr(
        self, name: str, namespace: Optional[str] = None
    ) -> Dict[str, Any]:
        """Delete a Sandbox custom resource.

        Args:
            name: Sandbox name
            namespace: Kubernetes namespace

        Returns:
            Dict with operation result
        """
        namespace = namespace or DEFAULT_NAMESPACE

        logger.info(f"Deleting Sandbox CR {name} in namespace {namespace}")

        try:
            self.custom_api.delete_namespaced_custom_object(
                group=CRD_GROUP,
                version=CRD_VERSION,
                namespace=namespace,
                plural="sandboxes",
                name=name,
            )

            return {
                "name": name,
                "namespace": namespace,
                "deleted": True,
            }

        except ApiException as e:
            if e.status == 404:
                raise Exception(f"Sandbox {name} not found in namespace {namespace}")
            logger.error(f"Failed to delete Sandbox CR: {e}")
            raise Exception(f"Failed to delete sandbox: {e.reason}")

    async def update_sandbox_status(
        self,
        name: str,
        namespace: str,
        status_updates: Dict[str, Any],
    ) -> None:
        """Update the status of a Sandbox CR.

        Args:
            name: Sandbox name
            namespace: Kubernetes namespace
            status_updates: Dict of status fields to update
        """
        try:
            # Get current sandbox
            sandbox = self.custom_api.get_namespaced_custom_object(
                group=CRD_GROUP,
                version=CRD_VERSION,
                namespace=namespace,
                plural="sandboxes",
                name=name,
            )

            # Update status
            current_status = sandbox.get("status", {})
            current_status.update(status_updates)
            sandbox["status"] = current_status

            # Patch the status subresource
            self.custom_api.patch_namespaced_custom_object_status(
                group=CRD_GROUP,
                version=CRD_VERSION,
                namespace=namespace,
                plural="sandboxes",
                name=name,
                body=sandbox,
            )

        except ApiException as e:
            logger.error(f"Failed to update Sandbox status: {e}")
            raise

    async def wait_for_sandbox_ready(
        self,
        name: str,
        namespace: Optional[str] = None,
        timeout_seconds: int = 120,
    ) -> Dict[str, Any]:
        """Wait for a Sandbox to reach Running phase.

        Args:
            name: Sandbox name
            namespace: Kubernetes namespace
            timeout_seconds: Maximum time to wait

        Returns:
            Dict with sandbox details when ready
        """
        namespace = namespace or DEFAULT_NAMESPACE
        start_time = asyncio.get_event_loop().time()

        while True:
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed > timeout_seconds:
                raise Exception(
                    f"Sandbox {name} did not become ready within {timeout_seconds}s"
                )

            sandbox = await self.get_sandbox_cr(name, namespace)

            if sandbox["phase"] == "Running":
                return sandbox
            elif sandbox["phase"] == "Terminated":
                raise Exception(f"Sandbox {name} terminated unexpectedly")

            await asyncio.sleep(2)

    # =========================================================================
    # Pool Operations
    # =========================================================================

    async def claim_from_pool(
        self,
        pool_name: str,
        pvc_name: Optional[str] = None,
        namespace: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Claim a sandbox from a warm pool.

        Args:
            pool_name: Name of the SandboxPool
            pvc_name: Optional PVC to attach
            namespace: Kubernetes namespace

        Returns:
            Dict with claimed sandbox details
        """
        namespace = namespace or DEFAULT_NAMESPACE

        # Find unclaimed sandbox from pool
        sandboxes = await self.list_sandbox_crs(namespace=namespace, pool_name=pool_name)

        unclaimed = [
            s for s in sandboxes
            if s["phase"] == "Running" and not s.get("claimed")
        ]

        if not unclaimed:
            raise Exception(f"No available sandbox in pool {pool_name}")

        sandbox_name = unclaimed[0]["name"]

        # Mark as claimed and optionally attach PVC
        try:
            sandbox = self.custom_api.get_namespaced_custom_object(
                group=CRD_GROUP,
                version=CRD_VERSION,
                namespace=namespace,
                plural="sandboxes",
                name=sandbox_name,
            )

            # Add claimed label
            labels = sandbox["metadata"].get("labels", {})
            labels["ark.mckinsey.com/claimed"] = "true"
            sandbox["metadata"]["labels"] = labels

            # Optionally add PVC
            if pvc_name:
                sandbox["spec"]["pvcName"] = pvc_name

            self.custom_api.patch_namespaced_custom_object(
                group=CRD_GROUP,
                version=CRD_VERSION,
                namespace=namespace,
                plural="sandboxes",
                name=sandbox_name,
                body=sandbox,
            )

            return await self.get_sandbox_cr(sandbox_name, namespace)

        except ApiException as e:
            logger.error(f"Failed to claim sandbox: {e}")
            raise Exception(f"Failed to claim sandbox: {e.reason}")

    # =========================================================================
    # Pod Operations (used by controller)
    # =========================================================================

    def create_pod_spec(
        self,
        name: str,
        image: str,
        ttl_minutes: int,
        pvc_name: Optional[str] = None,
        cpu_limit: str = "1",
        memory_limit: str = "2Gi",
        cpu_request: str = "100m",
        memory_request: str = "256Mi",
        owner_reference: Optional[Dict[str, Any]] = None,
    ) -> client.V1Pod:
        """Create pod specification for sandbox."""
        volume_mounts = [
            client.V1VolumeMount(
                name="workspace",
                mount_path="/workspace",
            ),
        ]

        volumes = [
            client.V1Volume(
                name="workspace",
                empty_dir=client.V1EmptyDirVolumeSource(),
            ),
        ]

        # Add PVC mount if provided
        if pvc_name:
            volume_mounts.append(
                client.V1VolumeMount(
                    name="shared-data",
                    mount_path="/shared",
                ),
            )
            volumes.append(
                client.V1Volume(
                    name="shared-data",
                    persistent_volume_claim=client.V1PersistentVolumeClaimVolumeSource(
                        claim_name=pvc_name,
                    ),
                ),
            )

        # Calculate expiry time
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=ttl_minutes)

        metadata = client.V1ObjectMeta(
            name=name,
            labels={
                "ark.mckinsey.com/sandbox": "true",
                "ark.mckinsey.com/sandbox-name": name,
            },
            annotations={
                "ark.mckinsey.com/expires-at": expires_at.isoformat(),
            },
        )

        if owner_reference:
            metadata.owner_references = [
                client.V1OwnerReference(
                    api_version=owner_reference["apiVersion"],
                    kind=owner_reference["kind"],
                    name=owner_reference["name"],
                    uid=owner_reference["uid"],
                    controller=True,
                    block_owner_deletion=True,
                )
            ]

        return client.V1Pod(
            api_version="v1",
            kind="Pod",
            metadata=metadata,
            spec=client.V1PodSpec(
                containers=[
                    client.V1Container(
                        name="sandbox",
                        image=image,
                        command=["sleep", "infinity"],
                        resources=client.V1ResourceRequirements(
                            limits={
                                "cpu": cpu_limit,
                                "memory": memory_limit,
                            },
                            requests={
                                "cpu": cpu_request,
                                "memory": memory_request,
                            },
                        ),
                        volume_mounts=volume_mounts,
                    ),
                ],
                volumes=volumes,
                restart_policy="Never",
            ),
        )

    async def create_pod(
        self,
        name: str,
        namespace: str,
        image: str,
        ttl_minutes: int,
        pvc_name: Optional[str] = None,
        owner_reference: Optional[Dict[str, Any]] = None,
    ) -> client.V1Pod:
        """Create a sandbox pod.

        Args:
            name: Pod name
            namespace: Kubernetes namespace
            image: Container image
            ttl_minutes: Time-to-live in minutes
            pvc_name: Optional PVC to mount
            owner_reference: Optional owner reference for garbage collection

        Returns:
            Created pod object
        """
        pod_spec = self.create_pod_spec(
            name=name,
            image=image,
            ttl_minutes=ttl_minutes,
            pvc_name=pvc_name,
            owner_reference=owner_reference,
        )

        try:
            pod = self.core_v1.create_namespaced_pod(
                namespace=namespace,
                body=pod_spec,
            )
            logger.info(f"Created pod {name} in namespace {namespace}")
            return pod

        except ApiException as e:
            logger.error(f"Failed to create pod: {e}")
            raise

    async def delete_pod(self, name: str, namespace: str) -> None:
        """Delete a pod.

        Args:
            name: Pod name
            namespace: Kubernetes namespace
        """
        try:
            self.core_v1.delete_namespaced_pod(
                name=name,
                namespace=namespace,
                body=client.V1DeleteOptions(grace_period_seconds=0),
            )
            logger.info(f"Deleted pod {name} in namespace {namespace}")

        except ApiException as e:
            if e.status != 404:
                logger.error(f"Failed to delete pod: {e}")
                raise

    async def get_pod_status(self, name: str, namespace: str) -> Optional[str]:
        """Get pod phase.

        Args:
            name: Pod name
            namespace: Kubernetes namespace

        Returns:
            Pod phase or None if not found
        """
        try:
            pod = self.core_v1.read_namespaced_pod(name=name, namespace=namespace)
            return pod.status.phase

        except ApiException as e:
            if e.status == 404:
                return None
            raise

    async def get_pod_ip(self, name: str, namespace: str) -> Optional[str]:
        """Get pod IP address.

        Args:
            name: Pod name
            namespace: Kubernetes namespace

        Returns:
            Pod IP or None
        """
        try:
            pod = self.core_v1.read_namespaced_pod(name=name, namespace=namespace)
            return pod.status.pod_ip

        except ApiException as e:
            if e.status == 404:
                return None
            raise

    # =========================================================================
    # Command Execution (used by MCP tools)
    # =========================================================================

    async def execute_command(
        self,
        sandbox_name: str,
        command: str,
        namespace: Optional[str] = None,
        working_dir: str = "/workspace",
    ) -> Dict[str, Any]:
        """Execute command in sandbox.

        Args:
            sandbox_name: Sandbox name (CR name)
            command: Command to execute
            namespace: Kubernetes namespace
            working_dir: Working directory for command execution

        Returns:
            Dict with stdout, stderr, and exit code
        """
        namespace = namespace or DEFAULT_NAMESPACE

        # Get pod name from sandbox CR
        sandbox = await self.get_sandbox_cr(sandbox_name, namespace)

        if sandbox["phase"] != "Running":
            raise Exception(f"Sandbox {sandbox_name} is not running (phase: {sandbox['phase']})")

        pod_name = sandbox.get("podName")
        if not pod_name:
            raise Exception(f"Sandbox {sandbox_name} has no pod")

        logger.info(f"Executing command in {pod_name}: {command}")

        try:
            exec_command = [
                "/bin/sh",
                "-c",
                f"cd {working_dir} && {command}",
            ]

            resp = stream(
                self.core_v1.connect_get_namespaced_pod_exec,
                pod_name,
                namespace,
                command=exec_command,
                stderr=True,
                stdin=False,
                stdout=True,
                tty=False,
                _preload_content=False,
            )

            stdout_lines = []
            stderr_lines = []

            while resp.is_open():
                resp.update(timeout=1)
                if resp.peek_stdout():
                    stdout_lines.append(resp.read_stdout())
                if resp.peek_stderr():
                    stderr_lines.append(resp.read_stderr())

            resp.close()

            exit_code = 0
            if resp.returncode is not None:
                exit_code = resp.returncode

            return {
                "stdout": "".join(stdout_lines),
                "stderr": "".join(stderr_lines),
                "exit_code": exit_code,
                "command": command,
            }

        except ApiException as e:
            logger.error(f"Failed to execute command: {e}")
            raise Exception(f"Failed to execute command: {e.reason}")

    async def upload_file(
        self,
        sandbox_name: str,
        path: str,
        content: str,
        namespace: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Upload file to sandbox.

        Args:
            sandbox_name: Sandbox name
            path: File path in sandbox
            content: File content
            namespace: Kubernetes namespace

        Returns:
            Dict with operation result
        """
        namespace = namespace or DEFAULT_NAMESPACE

        logger.info(f"Uploading file to {sandbox_name}: {path}")

        import base64
        encoded_content = base64.b64encode(content.encode()).decode()

        # Ensure parent directory exists
        parent_dir = os.path.dirname(path)
        if parent_dir:
            await self.execute_command(
                sandbox_name=sandbox_name,
                command=f"mkdir -p {parent_dir}",
                namespace=namespace,
            )

        command = f'echo "{encoded_content}" | base64 -d > {path}'

        result = await self.execute_command(
            sandbox_name=sandbox_name,
            command=command,
            namespace=namespace,
            working_dir="/",
        )

        if result["exit_code"] != 0:
            raise Exception(f"Failed to upload file: {result['stderr']}")

        return {
            "path": path,
            "size": len(content),
            "success": True,
        }

    async def download_file(
        self,
        sandbox_name: str,
        path: str,
        namespace: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Download file from sandbox.

        Args:
            sandbox_name: Sandbox name
            path: File path in sandbox
            namespace: Kubernetes namespace

        Returns:
            Dict with file content
        """
        namespace = namespace or DEFAULT_NAMESPACE

        logger.info(f"Downloading file from {sandbox_name}: {path}")

        result = await self.execute_command(
            sandbox_name=sandbox_name,
            command=f"cat {path}",
            namespace=namespace,
            working_dir="/",
        )

        if result["exit_code"] != 0:
            raise Exception(f"Failed to download file: {result['stderr']}")

        return {
            "path": path,
            "content": result["stdout"],
        }

    async def get_sandbox_logs(
        self,
        sandbox_name: str,
        namespace: Optional[str] = None,
        tail_lines: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Get logs from sandbox pod.

        Args:
            sandbox_name: Sandbox name
            namespace: Kubernetes namespace
            tail_lines: Number of lines to retrieve from end

        Returns:
            Dict with log content
        """
        namespace = namespace or DEFAULT_NAMESPACE

        # Get pod name from sandbox CR
        sandbox = await self.get_sandbox_cr(sandbox_name, namespace)
        pod_name = sandbox.get("podName")

        if not pod_name:
            raise Exception(f"Sandbox {sandbox_name} has no pod")

        logger.info(f"Getting logs from {pod_name}")

        try:
            logs = self.core_v1.read_namespaced_pod_log(
                name=pod_name,
                namespace=namespace,
                tail_lines=tail_lines,
            )

            return {
                "sandbox_name": sandbox_name,
                "logs": logs,
            }

        except ApiException as e:
            if e.status == 404:
                raise Exception(f"Pod {pod_name} not found")
            logger.error(f"Failed to get sandbox logs: {e}")
            raise Exception(f"Failed to get sandbox logs: {e.reason}")

