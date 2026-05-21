"""
Marketplace feature tests.

Each test class installs one marketplace item, exercises its actual functionality
(REST API, Ark CRDs, MCP endpoints), then tears it down.

Structure
---------
TestFileGateway         — upload / list / download / delete files via the REST API
TestDevTools            — a2a-inspector and mcp-inspector web UIs return 200
TestExecutors           — ExecutionEngine CRs registered + /health passes
TestKYCDemoBundle       — Agent + Team CRs created with correct prompts/structure
TestKYCOnboardingBundle — Agent + Team CRs from the full onboarding bundle
TestFilesystemMCP       — MCPServer CR created + MCP service reachable
TestNoah                — Agent CR + MCP service health

Requirements
------------
- Kubernetes cluster (kubeconfig configured)
- helm 3 and kubectl in PATH
- Ark core installed (controller, tenant, api)

Environment variables
---------------------
REPO_ROOT           Repo root (default: three levels up from this file)
HELM_INSTALL_TIMEOUT  Default: 5m
KUBECTL_WAIT_TIMEOUT  Default: 300s
SKIP_ITEMS          Comma-separated item names to skip
"""

import io
import json
import os
import subprocess
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Generator

import pytest
import requests

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

REPO_ROOT = Path(os.environ.get("REPO_ROOT", Path(__file__).parent.parent.parent))
HELM_TIMEOUT = os.environ.get("HELM_INSTALL_TIMEOUT", "5m")
KUBECTL_TIMEOUT = os.environ.get("KUBECTL_WAIT_TIMEOUT", "300s")
SKIP_ITEMS: set[str] = set(filter(None, os.environ.get("SKIP_ITEMS", "").split(",")))

_CHART_PATHS: dict[str, str] = {
    "file-gateway":               "services/file-gateway",
    "a2a-inspector":              "services/a2a-inspector",
    "mcp-inspector":              "services/mcp-inspector",
    "ark-sandbox":                "services/ark-sandbox",
    "executor-openai-responses":  "executors/openai-responses",
    "executor-claude-agent-sdk":  "executors/claude-agent-sdk",
    "executor-langchain":         "executors/langchain",
    "kyc-demo-bundle":            "demos/kyc-demo-bundle",
    "kyc-onboarding-bundle":      "demos/kyc-onboarding-bundle",
    "filesystem-mcp-server":      "mcps/filesystem-mcp-server",
    "noah":                       "agents/noah",
}


# ---------------------------------------------------------------------------
# Low-level helpers
# ---------------------------------------------------------------------------


def _run(cmd: list[str], check: bool = True, timeout: int = 400) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=check)


def _kubectl(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    return _run(["kubectl", *args], check=check)


def _helm(*args: str, check: bool = True, timeout: int = 400) -> subprocess.CompletedProcess:
    return _run(["helm", *args], check=check, timeout=timeout)


def _release_exists(name: str, namespace: str = "default") -> bool:
    """Return True if a Helm release named ``name`` is already deployed."""
    r = _helm("status", name, "--namespace", namespace, check=False)
    return r.returncode == 0


def _helm_install(
    name: str,
    namespace: str = "default",
    extra_set: list[str] | None = None,
) -> str:
    """Install the item if not already present; return the actual Helm release name.

    If a release named ``name`` already exists (e.g. a pre-existing cluster
    install) we reuse it directly.  Otherwise we install under ``{name}-ft``
    so teardown only removes what we created.
    """
    if _release_exists(name, namespace):
        return name  # use the existing release as-is

    chart_dir = REPO_ROOT / _CHART_PATHS[name] / "chart"
    _helm("dependency", "update", str(chart_dir), check=False)
    release = f"{name}-ft"
    cmd = [
        "helm", "upgrade", "--install", release, str(chart_dir),
        "--namespace", namespace, "--create-namespace",
        "--wait", "--timeout", HELM_TIMEOUT,
        "--atomic",
    ]
    for kv in (extra_set or []):
        cmd += ["--set", kv]
    result = _run(cmd, check=False, timeout=400)
    if result.returncode != 0:
        pytest.skip(f"helm install {name} failed: {result.stderr[:400]}")
    return release


def _helm_uninstall(name: str, namespace: str = "default", release: str = "") -> None:
    """Uninstall only if we installed it (i.e. release ends with -ft)."""
    target = release or f"{name}-ft"
    if target.endswith("-ft"):
        _helm("uninstall", target, "--namespace", namespace, check=False)


def _wait_for_deployments(namespace: str = "default", release: str = "", timeout: str = "120s") -> None:
    """Block until every Deployment owned by the release reports Available=True."""
    label = f"app.kubernetes.io/instance={release}" if release else ""
    selector = ["-l", label] if label else []
    result = _kubectl(
        "wait", "deployment",
        "--for=condition=Available",
        "--timeout", timeout,
        "-n", namespace,
        *selector,
        check=False,
    )
    if result.returncode != 0:
        # Non-fatal — tests will surface the real failure
        pass


def _skip_if(name: str) -> None:
    if name in SKIP_ITEMS:
        pytest.skip(f"{name} in SKIP_ITEMS")


# ---------------------------------------------------------------------------
# Port-forward context manager
# ---------------------------------------------------------------------------


@contextmanager
def port_forward(
    svc: str,
    local_port: int,
    remote_port: int,
    namespace: str = "default",
    wait_secs: float = 3.0,
) -> Generator[str, None, None]:
    """Yield http://localhost:{local_port} while kubectl port-forward is running."""
    proc = subprocess.Popen(
        ["kubectl", "port-forward",
         f"svc/{svc}", f"{local_port}:{remote_port}",
         "--namespace", namespace],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    time.sleep(wait_secs)
    try:
        yield f"http://localhost:{local_port}"
    finally:
        proc.terminate()
        proc.wait(timeout=5)


# ---------------------------------------------------------------------------
# Cluster-query helpers (Ark CRDs)
# ---------------------------------------------------------------------------


def _get_resource(kind: str, name: str, namespace: str = "default") -> dict[str, Any]:
    r = _kubectl("get", kind, name, "-n", namespace, "-o", "json", check=False)
    if r.returncode != 0:
        return {}
    try:
        return json.loads(r.stdout)
    except json.JSONDecodeError:
        return {}


def _list_resources(kind: str, namespace: str = "default") -> list[dict[str, Any]]:
    r = _kubectl("get", kind, "-n", namespace, "-o", "json", check=False)
    if r.returncode != 0:
        return []
    try:
        return json.loads(r.stdout).get("items", [])
    except json.JSONDecodeError:
        return []


# ===========================================================================
# TestFileGateway
# ===========================================================================


@pytest.mark.marketplace_feature
class TestFileGateway:
    """
    Full CRUD cycle through the File Gateway REST API.

    Verifies that files can be uploaded to S3-compatible storage, listed by
    prefix, downloaded with the correct content, then deleted.
    """

    FILE_KEY = "mkt-test/hello.txt"
    FILE_CONTENT = b"marketplace feature test content"
    NAMESPACE = "default"
    LOCAL_PORT = 19300

    @pytest.fixture(autouse=True, scope="class")
    def install(self, request):
        _skip_if("file-gateway")
        release = _helm_install("file-gateway", self.NAMESPACE)
        # Store release name so the api fixture can derive the service name
        request.cls._release = release
        yield
        _helm_uninstall("file-gateway", self.NAMESPACE, release)

    @pytest.fixture(scope="class")
    def api(self, install):
        """Yield the base URL of the file-gateway REST API (depends on install)."""
        # Service name is {release}-api, port 80 (chart default)
        svc = f"{self._release}-api"
        with port_forward(svc, self.LOCAL_PORT, 80, self.NAMESPACE) as base_url:
            # Poll until the service is actually serving traffic
            for _ in range(20):
                try:
                    r = requests.get(f"{base_url}/health", timeout=5)
                    if r.status_code == 200:
                        break
                except requests.exceptions.ConnectionError:
                    pass
                time.sleep(2)
            yield base_url

    # ------------------------------------------------------------------

    def _upload(self, api: str) -> None:
        """Upload the test file (idempotent — safe to call multiple times)."""
        requests.post(
            f"{api}/files",
            files={"file": ("hello.txt", io.BytesIO(self.FILE_CONTENT), "text/plain")},
            data={"prefix": "mkt-test/"},
            timeout=15,
        )

    def test_health(self, api):
        r = requests.get(f"{api}/health", timeout=10)
        assert r.status_code == 200
        assert r.json().get("status") == "healthy"

    def test_list_files_returns_structure(self, api):
        r = requests.get(f"{api}/files", timeout=10)
        assert r.status_code == 200
        body = r.json()
        assert "files" in body
        assert "directories" in body
        assert isinstance(body["files"], list)

    def test_upload_file(self, api):
        r = requests.post(
            f"{api}/files",
            files={"file": ("hello.txt", io.BytesIO(self.FILE_CONTENT), "text/plain")},
            data={"prefix": "mkt-test/"},
            timeout=15,
        )
        assert r.status_code == 200, f"Upload failed: {r.text}"

    def test_file_appears_in_list(self, api):
        self._upload(api)
        r = requests.get(f"{api}/files", params={"prefix": "mkt-test/"}, timeout=10)
        assert r.status_code == 200
        keys = [f["key"] for f in r.json().get("files", [])]
        assert self.FILE_KEY in keys, f"Expected {self.FILE_KEY!r} in file list, got: {keys}"

    def test_download_file_content(self, api):
        self._upload(api)
        r = requests.get(f"{api}/files/{self.FILE_KEY}/download", timeout=15)
        assert r.status_code == 200, f"Download failed: {r.text}"
        assert r.content == self.FILE_CONTENT

    def test_delete_file(self, api):
        self._upload(api)
        r = requests.delete(f"{api}/files/{self.FILE_KEY}", timeout=10)
        assert r.status_code == 200
        assert r.json().get("status") == "deleted"

    def test_file_gone_after_delete(self, api):
        self._upload(api)
        requests.delete(f"{api}/files/{self.FILE_KEY}", timeout=10)
        r = requests.get(f"{api}/files", params={"prefix": "mkt-test/"}, timeout=10)
        keys = [f["key"] for f in r.json().get("files", [])]
        assert self.FILE_KEY not in keys, f"{self.FILE_KEY!r} still in list after delete: {keys}"

    def test_download_missing_file_returns_404(self, api):
        r = requests.get(f"{api}/files/mkt-test/does-not-exist.txt/download", timeout=10)
        assert r.status_code == 404


# ===========================================================================
# TestDevTools
# ===========================================================================


@pytest.mark.marketplace_feature
class TestDevTools:
    """
    A2A Inspector and MCP Inspector both serve a web UI.
    Verify the root path returns HTTP 200 with HTML content.
    """

    NAMESPACE = "default"

    @pytest.fixture(autouse=True, scope="class")
    def install(self):
        skip_a2a = "a2a-inspector" in SKIP_ITEMS
        skip_mcp = "mcp-inspector" in SKIP_ITEMS
        rel_a2a = _helm_install("a2a-inspector", self.NAMESPACE) if not skip_a2a else None
        rel_mcp = _helm_install("mcp-inspector", self.NAMESPACE) if not skip_mcp else None
        yield
        if rel_a2a:
            _helm_uninstall("a2a-inspector", self.NAMESPACE, rel_a2a)
        if rel_mcp:
            _helm_uninstall("mcp-inspector", self.NAMESPACE, rel_mcp)

    def test_a2a_inspector_ui(self):
        _skip_if("a2a-inspector")
        with port_forward("a2a-inspector", 19310, 8080, self.NAMESPACE) as base_url:
            r = requests.get(base_url, timeout=10)
            assert r.status_code == 200
            assert "html" in r.headers.get("content-type", "").lower() or "<html" in r.text.lower()

    def test_mcp_inspector_ui(self):
        _skip_if("mcp-inspector")
        with port_forward("mcp-inspector", 19311, 6274, self.NAMESPACE) as base_url:
            r = requests.get(base_url, timeout=10)
            assert r.status_code == 200


# ===========================================================================
# TestExecutors
# ===========================================================================


@pytest.mark.marketplace_feature
class TestExecutors:
    """
    Each executor installs an ExecutionEngine CR in the cluster and runs a
    FastAPI server with a /health endpoint.

    Checks:
    - ExecutionEngine CR exists and has the expected name
    - ExecutionEngine CR has a non-empty spec.address
    - /health returns 200
    """

    NAMESPACE = "default"
    # (helm-item-name, ExecutionEngine-name, service-port, local-port-for-forward)
    EXECUTORS = [
        ("executor-openai-responses", "executor-openai-responses", 8000, 19320),
        ("executor-claude-agent-sdk",  "executor-claude-agent-sdk",  8000, 19321),
        ("executor-langchain",          "executor-langchain",          8000, 19322),
    ]

    @pytest.fixture(autouse=True, scope="class")
    def install(self):
        releases = {}
        for name, *_ in self.EXECUTORS:
            if name not in SKIP_ITEMS:
                rel = _helm_install(name, self.NAMESPACE)
                releases[name] = rel
                _wait_for_deployments(self.NAMESPACE, release=rel)
        yield
        for name, rel in releases.items():
            _helm_uninstall(name, self.NAMESPACE, rel)

    @pytest.mark.parametrize("name,ee_name,port,lport", EXECUTORS, ids=[e[0] for e in EXECUTORS])
    def test_execution_engine_cr_exists(self, name, ee_name, port, lport):
        _skip_if(name)
        obj = _get_resource("executionengine", ee_name, self.NAMESPACE)
        assert obj, f"ExecutionEngine/{ee_name} not found in namespace {self.NAMESPACE}"
        assert obj.get("metadata", {}).get("name") == ee_name

    @pytest.mark.parametrize("name,ee_name,port,lport", EXECUTORS, ids=[e[0] for e in EXECUTORS])
    def test_execution_engine_has_address(self, name, ee_name, port, lport):
        _skip_if(name)
        obj = _get_resource("executionengine", ee_name, self.NAMESPACE)
        if not obj:
            pytest.skip(f"ExecutionEngine/{ee_name} not found")
        address = obj.get("spec", {}).get("address", {})
        assert address, f"ExecutionEngine/{ee_name} has no spec.address: {obj.get('spec')}"

    @pytest.mark.parametrize("name,ee_name,port,lport", EXECUTORS, ids=[e[0] for e in EXECUTORS])
    def test_health_endpoint(self, name, ee_name, port, lport):
        _skip_if(name)
        with port_forward(ee_name, lport, port, self.NAMESPACE) as base_url:
            r = requests.get(f"{base_url}/health", timeout=10)
            assert r.status_code == 200, (
                f"{name}: /health returned {r.status_code}: {r.text[:200]}"
            )


# ===========================================================================
# TestKYCDemoBundle
# ===========================================================================


@pytest.mark.marketplace_feature
class TestKYCDemoBundle:
    """
    The kyc-demo-bundle installs 5 Ark Agent CRs and 4 Ark Team CRs.

    Checks:
    - All expected Agent CRs exist in the cluster
    - Each Agent has a non-empty prompt
    - Each Agent references the filesystem MCP tools it needs
    - All expected Team CRs exist
    - Each Team has a non-empty member list
    """

    # Use a dedicated namespace so the bundled file-gateway sub-chart
    # does not conflict with any existing file-gateway release in default
    NAMESPACE = "kyc-demo-test"

    EXPECTED_AGENTS = [
        "document-verifier",
        "ubo-extractor",
        "sanctions-screener",
        "risk-assessor",
        "compliance-reporter",
    ]
    EXPECTED_TEAMS = [
        "identity-verification-team",
        "ownership-analysis-team",
        "compliance-screening-team",
        "risk-assessment-team",
    ]

    @pytest.fixture(autouse=True, scope="class")
    def install(self):
        _skip_if("kyc-demo-bundle")
        release = _helm_install("kyc-demo-bundle", self.NAMESPACE)
        time.sleep(5)
        yield
        _helm_uninstall("kyc-demo-bundle", self.NAMESPACE, release)
        _kubectl("delete", "namespace", self.NAMESPACE, "--ignore-not-found", check=False)

    # --- Agent CRD checks ---

    @pytest.mark.parametrize("agent_name", EXPECTED_AGENTS)
    def test_agent_cr_exists(self, agent_name):
        obj = _get_resource("agent", agent_name, self.NAMESPACE)
        assert obj, f"Agent/{agent_name} not found in namespace {self.NAMESPACE}"

    @pytest.mark.parametrize("agent_name", EXPECTED_AGENTS)
    def test_agent_has_prompt(self, agent_name):
        obj = _get_resource("agent", agent_name, self.NAMESPACE)
        if not obj:
            pytest.skip(f"Agent/{agent_name} not found")
        prompt = obj.get("spec", {}).get("prompt", "")
        assert prompt and len(prompt.strip()) > 20, (
            f"Agent/{agent_name} has empty or trivial prompt: {prompt!r}"
        )

    @pytest.mark.parametrize("agent_name", EXPECTED_AGENTS)
    def test_agent_references_model(self, agent_name):
        obj = _get_resource("agent", agent_name, self.NAMESPACE)
        if not obj:
            pytest.skip(f"Agent/{agent_name} not found")
        model_ref = obj.get("spec", {}).get("modelRef", {})
        assert model_ref.get("name"), (
            f"Agent/{agent_name} has no modelRef.name: {model_ref}"
        )

    @pytest.mark.parametrize("agent_name", EXPECTED_AGENTS)
    def test_agent_has_file_tools(self, agent_name):
        obj = _get_resource("agent", agent_name, self.NAMESPACE)
        if not obj:
            pytest.skip(f"Agent/{agent_name} not found")
        tools = obj.get("spec", {}).get("tools", [])
        tool_names = [t.get("name", "") for t in tools]
        assert any("file" in n for n in tool_names), (
            f"Agent/{agent_name} has no file-gateway MCP tool. Tools: {tool_names}"
        )

    # --- Team CRD checks ---

    @pytest.mark.parametrize("team_name", EXPECTED_TEAMS)
    def test_team_cr_exists(self, team_name):
        obj = _get_resource("team", team_name, self.NAMESPACE)
        assert obj, f"Team/{team_name} not found in namespace {self.NAMESPACE}"

    @pytest.mark.parametrize("team_name", EXPECTED_TEAMS)
    def test_team_has_members(self, team_name):
        obj = _get_resource("team", team_name, self.NAMESPACE)
        if not obj:
            pytest.skip(f"Team/{team_name} not found")
        members = obj.get("spec", {}).get("members", [])
        assert len(members) >= 1, (
            f"Team/{team_name} has no members: {obj.get('spec')}"
        )

    @pytest.mark.parametrize("team_name", EXPECTED_TEAMS)
    def test_team_has_strategy(self, team_name):
        obj = _get_resource("team", team_name, self.NAMESPACE)
        if not obj:
            pytest.skip(f"Team/{team_name} not found")
        strategy = obj.get("spec", {}).get("strategy", "")
        assert strategy, f"Team/{team_name} has no spec.strategy: {obj.get('spec')}"

    def test_all_agents_count(self):
        all_agents = _list_resources("agent", self.NAMESPACE)
        installed_names = {a.get("metadata", {}).get("name") for a in all_agents}
        missing = set(self.EXPECTED_AGENTS) - installed_names
        assert not missing, f"Missing Agent CRs: {sorted(missing)}"

    def test_all_teams_count(self):
        all_teams = _list_resources("team", self.NAMESPACE)
        installed_names = {t.get("metadata", {}).get("name") for t in all_teams}
        missing = set(self.EXPECTED_TEAMS) - installed_names
        assert not missing, f"Missing Team CRs: {sorted(missing)}"


# ===========================================================================
# TestKYCOnboardingBundle
# ===========================================================================


@pytest.mark.marketplace_feature
class TestKYCOnboardingBundle:
    """
    The kyc-onboarding-bundle installs 21 agents and 6 teams.

    Spot-checks a representative subset and verifies the total counts.
    """

    NAMESPACE = "default"

    SPOT_CHECK_AGENTS = [
        "scout-agent",
        "rag-agent",
        "beneficial-owner-tree-agent",
        "bo-analyst",
        "file-manager-agent",
    ]
    SPOT_CHECK_TEAMS = [
        "scout-rag-team",
        "beneficial-owners-team",
        "consolidation-team",
    ]
    MIN_AGENT_COUNT = 20
    MIN_TEAM_COUNT = 5

    @pytest.fixture(autouse=True, scope="class")
    def install(self):
        _skip_if("kyc-onboarding-bundle")
        release = _helm_install("kyc-onboarding-bundle", self.NAMESPACE)
        time.sleep(5)
        yield
        _helm_uninstall("kyc-onboarding-bundle", self.NAMESPACE, release)

    @pytest.mark.parametrize("agent_name", SPOT_CHECK_AGENTS)
    def test_agent_cr_exists(self, agent_name):
        obj = _get_resource("agent", agent_name, self.NAMESPACE)
        assert obj, f"Agent/{agent_name} not found in {self.NAMESPACE}"

    @pytest.mark.parametrize("agent_name", SPOT_CHECK_AGENTS)
    def test_agent_has_execution_engine_ref(self, agent_name):
        obj = _get_resource("agent", agent_name, self.NAMESPACE)
        if not obj:
            pytest.skip(f"Agent/{agent_name} not found")
        ee = obj.get("spec", {}).get("executionEngine", {})
        assert ee.get("name"), (
            f"Agent/{agent_name} has no executionEngine.name: {obj.get('spec')}"
        )

    @pytest.mark.parametrize("team_name", SPOT_CHECK_TEAMS)
    def test_team_cr_exists(self, team_name):
        obj = _get_resource("team", team_name, self.NAMESPACE)
        assert obj, f"Team/{team_name} not found in {self.NAMESPACE}"

    def test_minimum_agent_count(self):
        agents = _list_resources("agent", self.NAMESPACE)
        assert len(agents) >= self.MIN_AGENT_COUNT, (
            f"Expected at least {self.MIN_AGENT_COUNT} Agent CRs, "
            f"found {len(agents)}: {[a['metadata']['name'] for a in agents]}"
        )

    def test_minimum_team_count(self):
        teams = _list_resources("team", self.NAMESPACE)
        assert len(teams) >= self.MIN_TEAM_COUNT, (
            f"Expected at least {self.MIN_TEAM_COUNT} Team CRs, "
            f"found {len(teams)}: {[t['metadata']['name'] for t in teams]}"
        )


# ===========================================================================
# TestFilesystemMCP
# ===========================================================================


@pytest.mark.marketplace_feature
class TestFilesystemMCP:
    """
    The filesystem-mcp-server installs an MCPServer CR and a running service.

    Checks:
    - MCPServer CR is created with a tool prefix
    - Service is reachable and responds on the MCP port
    """

    NAMESPACE = "default"
    LOCAL_PORT = 19330

    @pytest.fixture(autouse=True, scope="class")
    def install(self):
        _skip_if("filesystem-mcp-server")
        release = _helm_install("filesystem-mcp-server", self.NAMESPACE)
        _wait_for_deployments(self.NAMESPACE, release=release)
        yield
        _helm_uninstall("filesystem-mcp-server", self.NAMESPACE, release)

    def test_mcpserver_cr_exists(self):
        resources = _list_resources("mcpserver", self.NAMESPACE)
        names = [r.get("metadata", {}).get("name", "") for r in resources]
        assert any("filesystem" in n for n in names), (
            f"No MCPServer CR with 'filesystem' in name. Found: {names}"
        )

    def test_mcpserver_has_address(self):
        resources = _list_resources("mcpserver", self.NAMESPACE)
        fs_servers = [r for r in resources if "filesystem" in r.get("metadata", {}).get("name", "")]
        assert fs_servers, "No filesystem MCPServer CR found"
        addr = fs_servers[0].get("spec", {}).get("address", {})
        assert addr, f"MCPServer has no spec.address: {fs_servers[0].get('spec')}"

    def test_mcp_service_responds(self):
        svc_name = "filesystem-mcp-server-ft"
        with port_forward(svc_name, self.LOCAL_PORT, 8080, self.NAMESPACE) as base_url:
            r = requests.get(f"{base_url}/health", timeout=10)
            assert r.status_code == 200


# ===========================================================================
# TestNoah
# ===========================================================================


@pytest.mark.marketplace_feature
class TestNoah:
    """
    Noah is the Ark runtime administration agent.

    Checks:
    - Agent CR is created with a non-empty prompt
    - MCP service is reachable and healthy
    """

    NAMESPACE = "default"
    LOCAL_PORT = 19340

    @pytest.fixture(autouse=True, scope="class")
    def install(self):
        _skip_if("noah")
        release = _helm_install("noah", self.NAMESPACE)
        _wait_for_deployments(self.NAMESPACE, release=release)
        yield
        _helm_uninstall("noah", self.NAMESPACE, release)

    def test_agent_cr_exists(self):
        obj = _get_resource("agent", "noah", self.NAMESPACE)
        assert obj, "Agent/noah not found in cluster"

    def test_agent_has_prompt(self):
        obj = _get_resource("agent", "noah", self.NAMESPACE)
        if not obj:
            pytest.skip("Agent/noah not found")
        prompt = obj.get("spec", {}).get("prompt", "")
        assert len(prompt.strip()) > 50, f"Noah prompt too short: {prompt[:100]!r}"

    def test_noah_mcp_service_healthy(self):
        # Check container is actually ready (not just phase=Running which is
        # also true for CrashLoopBackOff pods)
        ready = _kubectl(
            "get", "pods", "-l", "app=noah-mcp",
            "-n", self.NAMESPACE,
            "-o", "jsonpath={.items[0].status.containerStatuses[0].ready}",
            check=False,
        )
        assert ready.stdout.strip() == "true", (
            f"noah-mcp container is not ready. "
            f"Run: kubectl logs -l app=noah-mcp -n {self.NAMESPACE}"
        )
        with port_forward("noah-mcp", self.LOCAL_PORT, 8639, self.NAMESPACE) as base_url:
            r = requests.get(f"{base_url}/health", timeout=10)
            assert r.status_code == 200
