"""MCP Tools for sandbox operations."""

import logging
from typing import Annotated, Dict, Any, List, Optional
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

from k8s.manager import KubernetesManager

logger = logging.getLogger(__name__)


def register_tools(mcp: FastMCP, k8s_manager: KubernetesManager):
    """Register all MCP tools for sandbox operations."""

    @mcp.tool
    async def create_sandbox(
        image: Annotated[Optional[str], "Container image to use (default: python:3.12-slim)"] = None,
        namespace: Annotated[Optional[str], "Kubernetes namespace (default: 'default')"] = None,
        ttl_minutes: Annotated[Optional[int], "Time-to-live in minutes (default: 120)"] = None,
        pvc_name: Annotated[Optional[str], "Optional PVC name to mount at /shared for workflow data access"] = None,
    ) -> Dict[str, Any]:
        """Create a new sandbox container.

        Creates an isolated containerized environment where code can be executed,
        files can be managed, and development tasks can be performed. The sandbox
        will automatically be cleaned up after the TTL expires.

        If pvc_name is provided, the PVC will be mounted at /shared, allowing the
        sandbox to access workflow data and persist results.

        Returns:
            Dict containing sandbox name, namespace, image, status, ttlMinutes,
            and optionally pvcName and sharedPath if PVC is mounted
        """
        try:
            logger.info(f"Creating sandbox with image={image}, namespace={namespace}, ttl={ttl_minutes}, pvc={pvc_name}")

            # Create Sandbox CR
            result = await k8s_manager.create_sandbox_cr(
                image=image,
                namespace=namespace,
                ttl_minutes=ttl_minutes,
                pvc_name=pvc_name,
            )

            # Wait for sandbox to be ready
            sandbox = await k8s_manager.wait_for_sandbox_ready(
                result["name"],
                result["namespace"],
            )

            response = {
                "sandbox_id": sandbox["name"],
                "namespace": sandbox["namespace"],
                "image": sandbox["image"],
                "status": sandbox["phase"],
                "ttl_minutes": sandbox["ttlMinutes"],
            }

            if pvc_name:
                response["pvc_name"] = pvc_name
                response["shared_path"] = "/shared"

            return response

        except Exception as e:
            logger.error(f"Failed to create sandbox: {e}")
            raise ToolError(f"Failed to create sandbox: {str(e)}")

    @mcp.tool
    async def get_sandbox_info(
        sandbox_id: Annotated[str, "Sandbox identifier"],
        namespace: Annotated[Optional[str], "Kubernetes namespace (default: 'default')"] = None,
    ) -> Dict[str, Any]:
        """Get information about a sandbox.

        Retrieves the current status and metadata for an existing sandbox.
        Useful for checking if a sandbox is ready or still running.

        Returns:
            Dict containing sandbox details including status, image, created_at, ttl, and pod info
        """
        try:
            result = await k8s_manager.get_sandbox_cr(
                name=sandbox_id,
                namespace=namespace,
            )
            return {
                "sandbox_id": result["name"],
                "namespace": result["namespace"],
                "status": result["phase"],
                "image": result["image"],
                "pod_name": result["podName"],
                "pod_ip": result["podIP"],
                "ttl_minutes": result["ttlMinutes"],
                "started_at": result["startedAt"],
                "expires_at": result["expiresAt"],
            }
        except Exception as e:
            logger.error(f"Failed to get sandbox info: {e}")
            raise ToolError(f"Failed to get sandbox info: {str(e)}")

    @mcp.tool
    async def execute_command(
        sandbox_id: Annotated[str, "Sandbox identifier"],
        command: Annotated[str, "Shell command to execute"],
        working_dir: Annotated[str, "Working directory for execution (default: /workspace)"] = "/workspace",
        namespace: Annotated[Optional[str], "Kubernetes namespace (default: 'default')"] = None,
    ) -> Dict[str, Any]:
        """Execute a shell command in the sandbox.

        Runs a command inside the sandbox container and returns the output.
        Commands are executed via /bin/sh, so shell features like pipes and
        redirects are supported.

        Returns:
            Dict containing stdout, stderr, exit_code, and the executed command
        """
        try:
            logger.info(f"Executing command in {sandbox_id}: {command}")
            result = await k8s_manager.execute_command(
                sandbox_name=sandbox_id,
                command=command,
                namespace=namespace,
                working_dir=working_dir,
            )
            return result
        except Exception as e:
            logger.error(f"Failed to execute command: {e}")
            raise ToolError(f"Failed to execute command: {str(e)}")

    @mcp.tool
    async def upload_file(
        sandbox_id: Annotated[str, "Sandbox identifier"],
        path: Annotated[str, "File path in sandbox (relative to /workspace or absolute)"],
        content: Annotated[str, "File content to write"],
        namespace: Annotated[Optional[str], "Kubernetes namespace (default: 'default')"] = None,
    ) -> Dict[str, Any]:
        """Upload a file to the sandbox.

        Writes content to a file in the sandbox. Creates parent directories
        if they don't exist. The path can be relative to /workspace or absolute.

        Returns:
            Dict containing path, size, and success status
        """
        try:
            logger.info(f"Uploading file to {sandbox_id}: {path}")
            result = await k8s_manager.upload_file(
                sandbox_name=sandbox_id,
                path=path,
                content=content,
                namespace=namespace,
            )
            return result
        except Exception as e:
            logger.error(f"Failed to upload file: {e}")
            raise ToolError(f"Failed to upload file: {str(e)}")

    @mcp.tool
    async def download_file(
        sandbox_id: Annotated[str, "Sandbox identifier"],
        path: Annotated[str, "File path in sandbox to read"],
        namespace: Annotated[Optional[str], "Kubernetes namespace (default: 'default')"] = None,
    ) -> Dict[str, Any]:
        """Download a file from the sandbox.

        Reads the content of a file from the sandbox and returns it.

        Returns:
            Dict containing path and content
        """
        try:
            logger.info(f"Downloading file from {sandbox_id}: {path}")
            result = await k8s_manager.download_file(
                sandbox_name=sandbox_id,
                path=path,
                namespace=namespace,
            )
            return result
        except Exception as e:
            logger.error(f"Failed to download file: {e}")
            raise ToolError(f"Failed to download file: {str(e)}")

    @mcp.tool
    async def list_sandboxes(
        namespace: Annotated[Optional[str], "Kubernetes namespace (omit for all namespaces)"] = None,
    ) -> List[Dict[str, Any]]:
        """List all active sandboxes.

        Returns a list of all currently running sandbox containers, optionally
        filtered by namespace. If no namespace is specified, lists sandboxes
        across all namespaces.

        Returns:
            List of sandbox info dicts
        """
        try:
            result = await k8s_manager.list_sandbox_crs(namespace=namespace)
            return [
                {
                    "sandbox_id": s["name"],
                    "namespace": s["namespace"],
                    "status": s["phase"],
                    "image": s["image"],
                    "ttl_minutes": s["ttlMinutes"],
                    "started_at": s["startedAt"],
                }
                for s in result
            ]
        except Exception as e:
            logger.error(f"Failed to list sandboxes: {e}")
            raise ToolError(f"Failed to list sandboxes: {str(e)}")

    @mcp.tool
    async def delete_sandbox(
        sandbox_id: Annotated[str, "Sandbox identifier"],
        namespace: Annotated[Optional[str], "Kubernetes namespace (default: 'default')"] = None,
    ) -> Dict[str, Any]:
        """Delete a sandbox immediately.

        Permanently removes a sandbox container before its TTL expires.
        Use this to clean up sandboxes when you're done with them.

        Returns:
            Dict containing sandbox_id, namespace, and deleted status
        """
        try:
            logger.info(f"Deleting sandbox {sandbox_id}")
            result = await k8s_manager.delete_sandbox_cr(
                name=sandbox_id,
                namespace=namespace,
            )
            return {
                "sandbox_id": result["name"],
                "namespace": result["namespace"],
                "deleted": result["deleted"],
            }
        except Exception as e:
            logger.error(f"Failed to delete sandbox: {e}")
            raise ToolError(f"Failed to delete sandbox: {str(e)}")

    @mcp.tool
    async def get_sandbox_logs(
        sandbox_id: Annotated[str, "Sandbox identifier"],
        tail_lines: Annotated[Optional[int], "Number of lines from end to retrieve (omit for all)"] = None,
        namespace: Annotated[Optional[str], "Kubernetes namespace (default: 'default')"] = None,
    ) -> Dict[str, Any]:
        """Get logs from a sandbox container.

        Retrieves the stdout/stderr logs from the sandbox container. Useful
        for debugging or seeing output from long-running processes.

        Returns:
            Dict containing sandbox_id and logs
        """
        try:
            logger.info(f"Getting logs from {sandbox_id}")
            result = await k8s_manager.get_sandbox_logs(
                sandbox_name=sandbox_id,
                namespace=namespace,
                tail_lines=tail_lines,
            )
            return {
                "sandbox_id": sandbox_id,
                "logs": result["logs"],
            }
        except Exception as e:
            logger.error(f"Failed to get sandbox logs: {e}")
            raise ToolError(f"Failed to get sandbox logs: {str(e)}")

    @mcp.tool
    async def claim_sandbox_from_pool(
        pool_name: Annotated[str, "Name of the SandboxPool to claim from"],
        pvc_name: Annotated[Optional[str], "Optional PVC name to attach at /shared"] = None,
        namespace: Annotated[Optional[str], "Kubernetes namespace (default: 'default')"] = None,
    ) -> Dict[str, Any]:
        """Claim a warm sandbox from a pool.

        Claims an available sandbox from a warm pool. This is faster than
        creating a new sandbox because the pod is already running.

        Optionally attach a PVC to the claimed sandbox for data access.

        Returns:
            Dict containing sandbox details
        """
        try:
            logger.info(f"Claiming sandbox from pool {pool_name}")
            result = await k8s_manager.claim_from_pool(
                pool_name=pool_name,
                pvc_name=pvc_name,
                namespace=namespace,
            )
            return {
                "sandbox_id": result["name"],
                "namespace": result["namespace"],
                "status": result["phase"],
                "image": result["image"],
                "pod_name": result["podName"],
                "pod_ip": result["podIP"],
                "pvc_name": pvc_name,
                "shared_path": "/shared" if pvc_name else None,
            }
        except Exception as e:
            logger.error(f"Failed to claim sandbox from pool: {e}")
            raise ToolError(f"Failed to claim sandbox from pool: {str(e)}")

