"""ARK Runtime MCP Server implementation."""

import asyncio
import json
import os

from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

# Create MCP server with stateless HTTP to avoid session ID issues
mcp = FastMCP("ARK Runtime", stateless_http=True)

# Get port from environment with default
PORT = os.getenv("PORT", "8639")

@mcp.custom_route("/health", methods=["GET"])
async def health_check(request: Request) -> JSONResponse:
    """Health check endpoint."""
    return JSONResponse({"status": "healthy"})


@mcp.custom_route("/ready", methods=["GET"])
async def readiness_check(request: Request) -> JSONResponse:
    """Readiness check endpoint - verifies MCP server is ready by making a proper MCP request."""
    try:
        import httpx

        # Make a standard MCP tools/list request to enumerate available tools
        mcp_request = {
            "jsonrpc": "2.0",
            "id": "readiness-check",
            "method": "tools/list",
            "params": {},
        }

        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.post(
                f"http://localhost:{PORT}/mcp/",
                json=mcp_request,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json, text/event-stream",
                },
                timeout=2.0,
            )

            # Log for debugging
            print(
                f"DEBUG: MCP readiness check - Status: {response.status_code}",
                flush=True,
            )
            print(f"DEBUG: Response body: {response.text}", flush=True)

            # Now that server is stateless, we should get HTTP 200 for valid requests
            if response.status_code == 200:
                return JSONResponse({"status": "ready", "mcp_server": "responding"})
            else:
                return JSONResponse(
                    {"status": "not_ready", "http_code": response.status_code},
                    status_code=503,
                )

    except Exception as e:
        print(f"DEBUG: MCP readiness check exception: {str(e)}", flush=True)
        return JSONResponse({"status": "not_ready", "error": str(e)}, status_code=503)


async def run_command(command: str) -> str:
    """Execute a shell command and return structured JSON result."""
    try:
        process = await asyncio.create_subprocess_shell(
            command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()

        result = {
            "command": command,
            "stdout": stdout.decode().strip(),
            "stderr": stderr.decode().strip(),
            "statusCode": process.returncode,
        }

        return json.dumps(result, indent=2)
    except Exception as e:
        error_result = {
            "command": command,
            "stdout": "",
            "stderr": f"Exception: {str(e)}",
            "statusCode": -1,
        }
        return json.dumps(error_result, indent=2)


async def get_available_packages() -> str:
    """Read requirements.txt to show available Python packages."""
    try:
        result_json = await run_command("cat /app/requirements.txt")
        result = json.loads(result_json)
        if result["statusCode"] == 0 and result["stdout"]:
            return f"Available Python Packages:\n{result['stdout']}"
        else:
            return "Available Python Packages: requirements.txt not found"
    except Exception as e:
        return f"Could not read requirements.txt: {str(e)}"


@mcp.tool
async def kubectl(args: str) -> str:
    """Execute kubectl commands for Kubernetes cluster management.

    Use this tool for all kubectl operations. Provide the kubectl
    arguments as a single string (e.g., "get pods -n default").

    Args:
        args: kubectl command arguments (string)

    Returns:
        JSON string with structure:
        {
            "command": "kubectl <args>",
            "stdout": "command output",
            "stderr": "error output",
            "statusCode": 0
        }
    """
    return await run_command(f"kubectl {args}")


@mcp.tool
async def helm(args: str) -> str:
    """Execute helm commands for package management.

    Use this tool for all helm operations. Provide the helm
    arguments as a single string (e.g., "list -A").

    Args:
        args: helm command arguments (string)

    Returns:
        JSON string with structure:
        {
            "command": "helm <args>",
            "stdout": "command output",
            "stderr": "error output",
            "statusCode": 0
        }
    """
    return await run_command(f"helm {args}")


@mcp.tool
async def bash(command: str) -> str:
    """Execute bash commands on the system.

    Use for utilities without dedicated tools (wget, curl, jq, etc).
    Always prefer dedicated kubectl/helm tools over bash equivalents.

    Args:
        command: bash command to execute (string)

    Returns:
        JSON string with structure:
        {
            "command": "<command>",
            "stdout": "command output",
            "stderr": "error output",
            "statusCode": 0
        }
    """
    return await run_command(command)


@mcp.tool
async def python(code: str) -> str:
    """Execute Python code with access to installed packages.

    Args:
        code: Python code to execute (string)

    Returns:
        JSON string with structure:
        {
            "command": "python3 -c '<code>'",
            "stdout": "execution output",
            "stderr": "error output",
            "statusCode": 0
        }
    """
    return await run_command(f"python3 -c '{code}'")


@mcp.tool
async def system_info() -> str:
    """Get MCP server capabilities - shows tools available to agents through this server."""
    packages_info = await get_available_packages()

    info = "ARK Runtime MCP Server System Capabilities\n"
    info += "=" * 40 + "\n\n"
    info += "NOTE: These are runtime tools available to agents through this MCP server.\n"
    info += "They are focused on Kubernetes, infrastructure, and low-level operations.\n\n"

    info += "MCP Tools (agent-facing - ALWAYS prefer these over bash):\n"
    info += "  • kubectl - Kubernetes cluster management\n"
    info += "  • helm - Kubernetes package management\n"
    info += "  • python - Python code execution\n"
    info += "  • bash - Shell command execution (for tools without dedicated MCP tools)\n"
    info += "  • ark_status - ARK system status\n"
    info += "  • ark_runtime_101 - ARK runtime resource discovery and operational procedures\n"
    info += "  • system_info - This capability report\n\n"

    info += f"{packages_info}\n\n"

    info += "Tool Usage Priority:\n"
    info += "  1. ALWAYS use dedicated MCP tools when available\n"
    info += "  2. Use 'bash' only for utilities without MCP tools (wget, curl, jq, etc)\n"
    info += "  3. Use 'bash which <tool>' or 'bash ls /usr/bin' to discover additional binaries\n"

    return info


@mcp.tool
async def ark_status() -> str:
    """Check ARK system status and version.

    Returns:
        Formatted string with ARK version and pod status information
    """
    # Get ARK version from pod labels
    version_cmd = (
        "kubectl get pods -n ark-system -l app.kubernetes.io/name=ark "
        "-o jsonpath='{.items[0].metadata.labels.app\\.kubernetes\\.io/version}'"
    )
    version = await run_command(version_cmd)

    # Get pod status
    status_cmd = "kubectl get pods -n ark-system -l app.kubernetes.io/name=ark -o wide"
    status = await run_command(status_cmd)

    version_json = json.loads(version)
    status_json = json.loads(status)

    return f"ARK System Status:\n\nVersion: {version_json['stdout']}\n\nPod Status:\n{status_json['stdout']}"


@mcp.tool
async def ark_runtime_101() -> str:
    """Comprehensive ARK Runtime knowledge base for infrastructure and operations.

    Returns:
        Detailed documentation of ARK resources, runtime architecture, and operational procedures
    """
    # Get all ARK CRDs
    crd_cmd = "kubectl get crd | grep ark.mckinsey.com"
    crds_result = await run_command(crd_cmd)
    crds_json = json.loads(crds_result)

    # Get detailed schema for each CRD
    schemas = []
    ark_crds = [
        "agents.ark.mckinsey.com",
        "models.ark.mckinsey.com",
        "teams.ark.mckinsey.com",
        "queries.ark.mckinsey.com",
        "evaluators.ark.mckinsey.com",
        "executionengines.ark.mckinsey.com",
        "mcpservers.ark.mckinsey.com",
        "memories.ark.mckinsey.com",
        "tools.ark.mckinsey.com",
        "a2aservers.ark.mckinsey.com",
    ]

    for crd in ark_crds:
        schema_cmd = f"kubectl get crd {crd} -o jsonpath='{{.spec.versions[0].schema.openAPIV3Schema.properties.spec}}'"
        schema_result = await run_command(schema_cmd)
        schema_json = json.loads(schema_result)
        if schema_json["statusCode"] == 0 and schema_json["stdout"].strip():
            schemas.append(f"\n## {crd.split('.')[0].upper()}\n{schema_json['stdout']}")

    # Read comprehensive guide from markdown file
    try:
        guide_path = "/app/src/ark_runtime_mcp/ark_runtime_guide.md"
        with open(guide_path, "r") as f:
            comprehensive_guide = f.read()
    except FileNotFoundError:
        comprehensive_guide = (
            "ARK Runtime guide file not found. Please check the ark_runtime_guide.md "
            "file in the src/ark_runtime_mcp directory."
        )

    return (
        f"ARK Runtime Platform CRDs:\n\n{crds_json['stdout']}\n\n"
        f"Resource Schemas:{''.join(schemas)}\n{comprehensive_guide}"
    )


if __name__ == "__main__":
    print("📦 MCP Server: ark-runtime", flush=True)
    print(
        "🔧 Dedicated Tools: kubectl, helm, python, ark-status, ark-runtime-101, system-info",
        flush=True,
    )
    print("⚡ General Tool: bash (for utilities without dedicated tools)", flush=True)
    print(
        "🐍 Python: pandas, numpy, kubernetes, pyyaml, jinja2, requests, httpx, jsonpath-ng, dateutil",
        flush=True,
    )
    print("💡 ALWAYS prefer dedicated tools over bash when available", flush=True)
    mcp.run()
