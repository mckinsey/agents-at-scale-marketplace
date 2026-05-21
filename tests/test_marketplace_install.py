"""
Marketplace install-and-health checks.

Reads every item from marketplace.json, installs its local Helm chart into the
running Kubernetes cluster, verifies the deployment reaches Available, confirms
the expected Service exists, then tears down.

Requirements
------------
- A running Kubernetes cluster (kubeconfig in ~/.kube/config or KUBECONFIG env)
- helm 3 in PATH
- kubectl in PATH

Environment variables
---------------------
REPO_ROOT           Path to repo root (default: three levels up from this file)
HELM_INSTALL_TIMEOUT  helm --timeout value (default: 5m)
KUBECTL_WAIT_TIMEOUT  kubectl --timeout value (default: 300s)
SKIP_ITEMS          Comma-separated item names to skip (e.g. "langfuse,phoenix")
RELEASE_SUFFIX      Suffix appended to every helm release name (default: mkt-test)
                    Useful to avoid collisions when running in a shared cluster.
"""

import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any

import pytest

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

REPO_ROOT = Path(os.environ.get("REPO_ROOT", Path(__file__).parent.parent.parent))
MARKETPLACE_JSON = REPO_ROOT / "marketplace.json"

HELM_TIMEOUT = os.environ.get("HELM_INSTALL_TIMEOUT", "5m")
KUBECTL_TIMEOUT = os.environ.get("KUBECTL_WAIT_TIMEOUT", "300s")
RELEASE_SUFFIX = os.environ.get("RELEASE_SUFFIX", "mkt-test")
SKIP_ITEMS: set[str] = set(filter(None, os.environ.get("SKIP_ITEMS", "").split(",")))

# ---------------------------------------------------------------------------
# Item name → local chart path (relative to REPO_ROOT)
# All items in marketplace.json have a local chart directory.
# ---------------------------------------------------------------------------

LOCAL_CHART_PATHS: dict[str, str] = {
    # services
    "phoenix":                    "services/phoenix",
    "langfuse":                   "services/langfuse",
    "a2a-inspector":              "services/a2a-inspector",
    "mcp-inspector":              "services/mcp-inspector",
    "ark-sandbox":                "services/ark-sandbox",
    "file-gateway":               "services/file-gateway",
    # agents
    "noah":                       "agents/noah",
    # mcps
    "filesystem-mcp-server":      "mcps/filesystem-mcp-server",
    "speech-mcp-server":          "mcps/speech-mcp-server",
    "pdf-extraction-mcp":         "mcps/pdf-extraction-mcp",
    "web-research-mcp":           "mcps/web-research-mcp",
    "perplexity-ask-mcp":         "mcps/perplexity-ask-mcp",
    "companies-house-mcp":        "mcps/companies-house-mcp",
    # executors
    "executor-langchain":         "executors/langchain",
    "executor-claude-agent-sdk":  "executors/claude-agent-sdk",
    "executor-openai-responses":  "executors/openai-responses",
    # demos
    "kyc-demo-bundle":            "demos/kyc-demo-bundle",
    "cobol-modernization-bundle": "demos/cobol-modernization-bundle",
    "kyc-onboarding-bundle":      "demos/kyc-onboarding-bundle",
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run(cmd: list[str], check: bool = True, timeout: int = 400) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=check)


def _kubectl(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    return _run(["kubectl", *args], check=check)


def _helm(*args: str, check: bool = True, timeout: int = 400) -> subprocess.CompletedProcess:
    return _run(["helm", *args], check=check, timeout=timeout)


def _release_name(item_name: str) -> str:
    return f"{item_name}-{RELEASE_SUFFIX}"


def _chart_dir(item_name: str) -> Path:
    return REPO_ROOT / LOCAL_CHART_PATHS[item_name] / "chart"


# ---------------------------------------------------------------------------
# Load and parametrize items
# ---------------------------------------------------------------------------


def _load_items() -> list[dict[str, Any]]:
    data = json.loads(MARKETPLACE_JSON.read_text())
    items = []
    for item in data["items"]:
        name = item["name"]
        if name not in LOCAL_CHART_PATHS:
            continue
        if name in SKIP_ITEMS:
            continue
        items.append(item)
    return items


ALL_ITEMS = _load_items()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="function")
def installed_release(request):
    """Install the chart for the parametrized item, yield the release name, then uninstall."""
    item: dict[str, Any] = request.param
    name = item["name"]
    ark = item.get("ark", {})
    namespace = ark.get("namespace", "default")
    release = _release_name(name)
    chart_dir = _chart_dir(name)

    # Ensure chart dir exists
    assert chart_dir.exists(), f"Chart directory not found: {chart_dir}"

    # Update chart dependencies (no-op if none)
    dep_result = _helm(
        "dependency", "update", str(chart_dir),
        check=False,
    )
    if dep_result.returncode != 0:
        pytest.skip(f"helm dependency update failed for {name}: {dep_result.stderr[:300]}")

    # Install
    install_result = _helm(
        "upgrade", "--install", release, str(chart_dir),
        "--namespace", namespace,
        "--create-namespace",
        "--wait",
        "--timeout", HELM_TIMEOUT,
        check=False,
        timeout=int(HELM_TIMEOUT.rstrip("ms")) * 60 + 60,
    )

    yield {
        "item": item,
        "release": release,
        "namespace": namespace,
        "install_ok": install_result.returncode == 0,
        "install_stdout": install_result.stdout,
        "install_stderr": install_result.stderr,
    }

    # Always tear down
    _helm("uninstall", release, "--namespace", namespace, check=False)


# ---------------------------------------------------------------------------
# Tests — one class parametrized over all marketplace items
# ---------------------------------------------------------------------------


@pytest.mark.marketplace_install
@pytest.mark.parametrize("installed_release", ALL_ITEMS, indirect=True, ids=[i["name"] for i in ALL_ITEMS])
class TestMarketplaceInstall:
    """Install every marketplace item and verify it reaches a healthy state."""

    # ------------------------------------------------------------------
    # 1. Helm install succeeds
    # ------------------------------------------------------------------

    def test_helm_install_succeeds(self, installed_release):
        ctx = installed_release
        assert ctx["install_ok"], (
            f"{ctx['item']['name']}: helm install failed.\n"
            f"stdout: {ctx['install_stdout'][:500]}\n"
            f"stderr: {ctx['install_stderr'][:500]}"
        )

    # ------------------------------------------------------------------
    # 2. Helm status shows "deployed"
    # ------------------------------------------------------------------

    def test_helm_status_deployed(self, installed_release):
        ctx = installed_release
        if not ctx["install_ok"]:
            pytest.skip("install failed — skipping status check")

        result = _helm(
            "status", ctx["release"],
            "--namespace", ctx["namespace"],
            "--output", "json",
        )
        status_json = json.loads(result.stdout)
        assert status_json.get("info", {}).get("status") == "deployed", (
            f"{ctx['item']['name']}: expected helm status=deployed, "
            f"got: {status_json.get('info', {}).get('status')}"
        )

    # ------------------------------------------------------------------
    # 3. Primary deployment is Available (items that declare k8sDeploymentName)
    # ------------------------------------------------------------------

    def test_deployment_available(self, installed_release):
        ctx = installed_release
        if not ctx["install_ok"]:
            pytest.skip("install failed — skipping deployment check")

        deployment_name = ctx["item"].get("ark", {}).get("k8sDeploymentName")
        if not deployment_name:
            pytest.skip(f"{ctx['item']['name']} has no k8sDeploymentName (demo/CRD-only item)")

        namespace = ctx["namespace"]

        result = _kubectl(
            "wait", "--for=condition=available",
            f"deployment/{deployment_name}",
            "--namespace", namespace,
            f"--timeout={KUBECTL_TIMEOUT}",
            check=False,
        )
        assert result.returncode == 0, (
            f"{ctx['item']['name']}: deployment/{deployment_name} did not reach Available.\n"
            f"{result.stderr[:500]}"
        )

    # ------------------------------------------------------------------
    # 4. Service exists and is reachable within the cluster
    # ------------------------------------------------------------------

    def test_service_exists(self, installed_release):
        ctx = installed_release
        if not ctx["install_ok"]:
            pytest.skip("install failed — skipping service check")

        ark = ctx["item"].get("ark", {})
        svc_name = ark.get("k8sServiceName")
        if not svc_name:
            pytest.skip(f"{ctx['item']['name']} has no k8sServiceName (demo/CRD-only item)")

        namespace = ctx["namespace"]
        result = _kubectl(
            "get", "svc", svc_name,
            "--namespace", namespace,
            "--output", "jsonpath={.metadata.name}",
            check=False,
        )
        assert result.returncode == 0 and result.stdout.strip() == svc_name, (
            f"{ctx['item']['name']}: Service/{svc_name} not found in namespace {namespace}.\n"
            f"{result.stderr[:300]}"
        )

    # ------------------------------------------------------------------
    # 5. Service has at least one ready endpoint (pods backing the service)
    # ------------------------------------------------------------------

    def test_service_has_ready_endpoints(self, installed_release):
        ctx = installed_release
        if not ctx["install_ok"]:
            pytest.skip("install failed — skipping endpoint check")

        ark = ctx["item"].get("ark", {})
        svc_name = ark.get("k8sServiceName")
        if not svc_name:
            pytest.skip(f"{ctx['item']['name']} has no k8sServiceName")

        namespace = ctx["namespace"]

        # Poll for up to KUBECTL_WAIT_TIMEOUT seconds for ready addresses
        deadline = time.time() + int(KUBECTL_TIMEOUT.rstrip("s"))
        while True:
            result = _kubectl(
                "get", "endpoints", svc_name,
                "--namespace", namespace,
                "--output", "jsonpath={.subsets[0].addresses[0].ip}",
                check=False,
            )
            if result.returncode == 0 and result.stdout.strip():
                return  # at least one ready endpoint found

            if time.time() >= deadline:
                # Gather diagnostics
                pods = _kubectl(
                    "get", "pods", "--namespace", namespace,
                    "--output", "wide", check=False,
                ).stdout
                assert False, (
                    f"{ctx['item']['name']}: Service/{svc_name} has no ready endpoints "
                    f"after {KUBECTL_TIMEOUT}.\nPods:\n{pods}"
                )
            time.sleep(5)

    # ------------------------------------------------------------------
    # 6. Health endpoint returns HTTP 200 (executors and services that expose /health)
    # ------------------------------------------------------------------

    def test_health_endpoint(self, installed_release):
        ctx = installed_release
        if not ctx["install_ok"]:
            pytest.skip("install failed — skipping health check")

        ark = ctx["item"].get("ark", {})
        svc_name = ark.get("k8sServiceName")
        svc_port = ark.get("k8sServicePort")
        if not svc_name or not svc_port:
            pytest.skip(f"{ctx['item']['name']}: no service/port declared — skipping /health")

        namespace = ctx["namespace"]
        # Only executor and MCP items expose /health — skip services that don't
        item_type = ctx["item"].get("type", "")
        if item_type not in ("executor", "mcp"):
            pytest.skip(f"{ctx['item']['name']} is type={item_type} — no /health endpoint")

        # Port-forward to the service and curl /health
        pf = subprocess.Popen(
            ["kubectl", "port-forward",
             f"svc/{svc_name}", f"19200:{svc_port}",
             "--namespace", namespace],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        try:
            time.sleep(3)
            result = _run(
                ["curl", "-sf", "-o", "/dev/null", "-w", "%{http_code}",
                 "http://localhost:19200/health"],
                check=False,
                timeout=15,
            )
            assert result.stdout.strip() == "200", (
                f"{ctx['item']['name']}: /health returned HTTP {result.stdout.strip()!r} "
                f"(expected 200)"
            )
        finally:
            pf.terminate()
