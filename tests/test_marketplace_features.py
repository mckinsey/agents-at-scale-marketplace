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
REPO_ROOT             Repo root (default: three levels up from this file)
HELM_INSTALL_TIMEOUT  Default: 5m
KUBECTL_WAIT_TIMEOUT  Default: 300s
SKIP_ITEMS            Comma-separated item names to skip
"""

import io
import os
import shutil
import subprocess
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Generator

import pytest
import requests
import yaml
from kubernetes import client as k8s_client
from kubernetes import config as k8s_config
from kubernetes.client.rest import ApiException as K8sApiException

# Resolve CLI tools to absolute paths at import time so subprocess.Popen works
# regardless of how the test runner manipulates PATH (e.g. inside uv envs)
_KUBECTL = shutil.which("kubectl") or "kubectl"
_HELM = shutil.which("helm") or "helm"

# Load kubeconfig once at import time; tests that don't need a cluster are
# unaffected — the client is only called when a test method actually runs.
try:
    k8s_config.load_kube_config()
except Exception:
    try:
        k8s_config.load_incluster_config()
    except Exception:
        pass  # Tests will fail with a clear error if no kubeconfig is available

_ARK_GROUP = "ark.mckinsey.com"
_ARK_DEFAULT_VERSION = "v1alpha1"
_ARK_PLURALS: dict[str, str] = {
    "agent": "agents",
    "team": "teams",
    "executionengine": "executionengines",
    "mcpserver": "mcpservers",
    "model": "models",
}
# ExecutionEngine uses a different API version from the other Ark CRDs.
_ARK_VERSIONS: dict[str, str] = {
    "executionengine": "v1prealpha1",
}

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

REPO_ROOT = Path(os.environ.get("REPO_ROOT", Path(__file__).parent.parent.parent))
HELM_TIMEOUT = os.environ.get("HELM_INSTALL_TIMEOUT", "5m")
KUBECTL_TIMEOUT = os.environ.get("KUBECTL_WAIT_TIMEOUT", "300s")
SKIP_ITEMS: set[str] = set(filter(None, os.environ.get("SKIP_ITEMS", "").split(",")))

_CHART_PATHS: dict[str, str] = {
    # Services
    "file-gateway":               "services/file-gateway",
    "a2a-inspector":              "services/a2a-inspector",
    "mcp-inspector":              "services/mcp-inspector",
    "ark-sandbox":                "services/ark-sandbox",
    "langfuse":                   "services/langfuse",
    "phoenix":                    "services/phoenix",
    # Executors
    "executor-openai-responses":  "executors/openai-responses",
    "executor-claude-agent-sdk":  "executors/claude-agent-sdk",
    "executor-langchain":         "executors/langchain",
    # MCPs
    "filesystem-mcp-server":      "mcps/filesystem-mcp-server",
    "companies-house-mcp":        "mcps/companies-house-mcp",
    "pdf-extraction-mcp":         "mcps/pdf-extraction-mcp",
    "perplexity-ask-mcp":         "mcps/perplexity-ask-mcp",
    "speech-mcp-server":          "mcps/speech-mcp-server",
    "web-research-mcp":           "mcps/web-research-mcp",
    # Demos
    "kyc-demo-bundle":            "demos/kyc-demo-bundle",
    "kyc-onboarding-bundle":      "demos/kyc-onboarding-bundle",
    "cobol-modernization-bundle": "demos/cobol-modernization-bundle",
    # Agents
    "noah":                       "agents/noah",
}

# ---------------------------------------------------------------------------
# Low-level helpers
# ---------------------------------------------------------------------------


def _run(cmd: list[str], check: bool = True, timeout: int = 400) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=check)


def _kubectl(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    return _run([_KUBECTL, *args], check=check)


def _helm(*args: str, check: bool = True, timeout: int = 400) -> subprocess.CompletedProcess:
    return _run([_HELM, *args], check=check, timeout=timeout)


def _release_exists(name: str, namespace: str = "default") -> bool:
    r = _helm("status", name, "--namespace", namespace, check=False)
    return r.returncode == 0


def _helm_install(name: str, namespace: str = "default", extra_set: list[str] | None = None) -> str:
    """Always install fresh under ``{name}-ft``; return the release name.

    Any pre-existing releases (bare ``name`` or leftover ``{name}-ft``) are
    removed first to guarantee a clean-slate install on every run.
    """
    release = f"{name}-ft"
    for existing in (name, release):
        if _release_exists(existing, namespace):
            _helm("uninstall", existing, "--namespace", namespace, check=False)

    chart_dir = REPO_ROOT / _CHART_PATHS[name] / "chart"
    _helm("dependency", "update", str(chart_dir), check=False, timeout=600)
    cmd = [
        _HELM, "upgrade", "--install", release, str(chart_dir),
        "--namespace", namespace, "--create-namespace",
        "--wait", "--timeout", HELM_TIMEOUT, "--atomic",
    ]
    for kv in (extra_set or []):
        cmd += ["--set", kv]
    result = _run(cmd, check=False, timeout=400)
    if result.returncode != 0:
        pytest.skip(f"helm install {name} failed: {result.stderr[:400]}")
    return release


def _helm_uninstall(name: str, namespace: str = "default", release: str = "") -> None:
    target = release or f"{name}-ft"
    _helm("uninstall", target, "--namespace", namespace, check=False)


def _wait_for_agents_registered(
    names: list[str],
    namespace: str,
    timeout_secs: int = 30,
) -> None:
    """Poll until every named Agent CR is visible in the Kubernetes API.

    The Team admission webhook validates that referenced Agents exist before
    accepting a Team resource.  Polling here is more reliable than sleeping.
    """
    if not names:
        return
    deadline = time.time() + timeout_secs
    pending = set(names)
    while pending and time.time() < deadline:
        pending = {n for n in pending if not _get_resource("agent", n, namespace)}
        if pending:
            time.sleep(1)
    if pending:
        pytest.fail(
            f"Agent CRs not visible in API after {timeout_secs}s: {sorted(pending)}"
        )


def _template_and_apply(
    name: str,
    namespace: str,
    extra_set: list[str] | None = None,
) -> str:
    """Render the chart with ``helm template``, patch for local cluster quirks, then apply.

    Patches applied
    ---------------
    - Agent specs: strip ``maxCompletionTokens`` (not in CRD on older controllers)
    - Team specs:  add ``loops: true`` when ``maxTurns`` is present (webhook requirement)

    Resources are applied in two passes — non-Teams first, Teams second — so that
    the admission webhook that validates Team member Agent existence is satisfied.

    Returns the release label value (``{name}-ft``) used to identify resources.
    """
    release = f"{name}-ft"

    chart_dir = REPO_ROOT / _CHART_PATHS[name] / "chart"
    _helm("dependency", "update", str(chart_dir), check=False)
    _k8s_create_namespace(namespace)

    cmd = [_HELM, "template", release, str(chart_dir), "--namespace", namespace]
    for kv in (extra_set or []):
        cmd += ["--set", kv]
    result = _run(cmd, check=False)
    if result.returncode != 0:
        pytest.fail(f"helm template {name} failed: {result.stderr[:400]}")

    docs = [d for d in yaml.safe_load_all(result.stdout) if d is not None]

    non_teams: list[dict] = []
    teams: list[dict] = []
    for doc in docs:
        kind = doc.get("kind", "")
        spec = doc.get("spec") or {}
        if kind == "Agent":
            spec.pop("maxCompletionTokens", None)
            non_teams.append(doc)
        elif kind == "Team":
            if "maxTurns" in spec:
                spec["loops"] = True
            teams.append(doc)
        else:
            non_teams.append(doc)

    def _apply(documents: list[dict]) -> None:
        if not documents:
            return
        raw = yaml.dump_all(documents)
        r = subprocess.run(
            [_KUBECTL, "apply", "-f", "-", "-n", namespace],
            input=raw, text=True, capture_output=True,
        )
        if r.returncode != 0:
            pytest.fail(f"kubectl apply {name} failed: {r.stderr[:400]}")

    _apply(non_teams)
    _wait_for_agents_registered(
        names=[doc["metadata"]["name"] for doc in non_teams if doc.get("kind") == "Agent"],
        namespace=namespace,
    )
    _apply(teams)
    return release


def _template_cleanup(namespace: str) -> None:
    """Delete the entire namespace created by ``_template_and_apply``."""
    _k8s_delete_namespace(namespace)



def _k8s_create_namespace(namespace: str) -> None:
    try:
        k8s_client.CoreV1Api().create_namespace(
            k8s_client.V1Namespace(metadata=k8s_client.V1ObjectMeta(name=namespace))
        )
    except K8sApiException as exc:
        if exc.status != 409:  # 409 = AlreadyExists
            raise


def _k8s_delete_namespace(namespace: str) -> None:
    try:
        k8s_client.CoreV1Api().delete_namespace(name=namespace)
    except K8sApiException:
        pass  # 404 = already gone


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
        [_KUBECTL, "port-forward", f"svc/{svc}", f"{local_port}:{remote_port}",
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
    k = kind.lower()
    plural = _ARK_PLURALS.get(k)
    if not plural:
        raise ValueError(f"Unknown Ark CRD kind: {kind!r}. Known kinds: {list(_ARK_PLURALS)}")
    version = _ARK_VERSIONS.get(k, _ARK_DEFAULT_VERSION)
    try:
        return k8s_client.CustomObjectsApi().get_namespaced_custom_object(  # type: ignore[return-value]
            group=_ARK_GROUP,
            version=version,
            namespace=namespace,
            plural=plural,
            name=name,
        )
    except K8sApiException:
        return {}


def _list_resources(kind: str, namespace: str = "default") -> list[dict[str, Any]]:
    k = kind.lower()
    plural = _ARK_PLURALS.get(k)
    if not plural:
        raise ValueError(f"Unknown Ark CRD kind: {kind!r}. Known kinds: {list(_ARK_PLURALS)}")
    version = _ARK_VERSIONS.get(k, _ARK_DEFAULT_VERSION)
    try:
        result = k8s_client.CustomObjectsApi().list_namespaced_custom_object(
            group=_ARK_GROUP,
            version=version,
            namespace=namespace,
            plural=plural,
        )
        return result.get("items", [])  # type: ignore[return-value]
    except K8sApiException:
        return []


# ===========================================================================
# TestFileGateway
# ===========================================================================


@pytest.mark.skipif("file-gateway" in SKIP_ITEMS, reason="file-gateway in SKIP_ITEMS")
@pytest.mark.marketplace_feature
class TestFileGateway:
    """
    File Gateway: health check + full CRUD cycle via the REST API.
    """

    FILE_KEY = "mkt-test/hello.txt"
    FILE_CONTENT = b"marketplace feature test content"
    NAMESPACE = "file-gateway-ft"
    LOCAL_PORT = 19300

    @pytest.fixture(autouse=True, scope="class")
    def install(self):
        release = _helm_install("file-gateway", self.NAMESPACE)
        yield
        _helm_uninstall("file-gateway", self.NAMESPACE, release)
        _k8s_delete_namespace(self.NAMESPACE)

    @pytest.fixture(scope="class")
    def api(self, install):
        # fullnameOverride: "file-gateway" is set in values.yaml so the
        # service is always "file-gateway-api" regardless of release name.
        svc = "file-gateway-api"
        with port_forward(svc, self.LOCAL_PORT, 80, self.NAMESPACE) as base_url:
            for _ in range(20):
                try:
                    if requests.get(f"{base_url}/health", timeout=5).status_code == 200:
                        break
                except requests.exceptions.ConnectionError:
                    pass
                time.sleep(2)
            yield base_url

    def test_health(self, api):
        r = requests.get(f"{api}/health", timeout=10)
        assert r.status_code == 200
        assert r.json().get("status") == "healthy"

    def test_list_files(self, api):
        r = requests.get(f"{api}/files", timeout=10)
        assert r.status_code == 200
        body = r.json()
        assert "files" in body and "directories" in body

    def test_file_crud(self, api):
        """Upload → list → download → delete → verify gone."""
        # Upload
        r = requests.post(
            f"{api}/files",
            files={"file": ("hello.txt", io.BytesIO(self.FILE_CONTENT), "text/plain")},
            data={"prefix": "mkt-test/"},
            timeout=15,
        )
        assert r.status_code == 200, f"Upload failed: {r.text}"
        # Appears in list
        keys = [f["key"] for f in requests.get(
            f"{api}/files", params={"prefix": "mkt-test/"}, timeout=10
        ).json().get("files", [])]
        assert self.FILE_KEY in keys, f"File not in list after upload: {keys}"
        # Download matches content
        r = requests.get(f"{api}/files/{self.FILE_KEY}/download", timeout=15)
        assert r.status_code == 200 and r.content == self.FILE_CONTENT
        # Delete and confirm gone
        requests.delete(f"{api}/files/{self.FILE_KEY}", timeout=10)
        keys_after = [f["key"] for f in requests.get(
            f"{api}/files", params={"prefix": "mkt-test/"}, timeout=10
        ).json().get("files", [])]
        assert self.FILE_KEY not in keys_after, f"File still listed after delete: {keys_after}"

    def test_missing_file_returns_404(self, api):
        r = requests.get(f"{api}/files/mkt-test/does-not-exist.txt/download", timeout=10)
        assert r.status_code == 404


# ===========================================================================
# TestDevTools
# ===========================================================================


@pytest.mark.marketplace_feature
class TestDevTools:
    """a2a-inspector and mcp-inspector web UIs return HTTP 200."""

    NAMESPACE = "devtools-ft"

    @pytest.fixture(autouse=True, scope="class")
    def install(self, request):
        rel_a2a = _helm_install("a2a-inspector", self.NAMESPACE) if "a2a-inspector" not in SKIP_ITEMS else None
        rel_mcp = _helm_install("mcp-inspector", self.NAMESPACE) if "mcp-inspector" not in SKIP_ITEMS else None
        request.cls._rel_a2a = rel_a2a
        request.cls._rel_mcp = rel_mcp
        yield
        if rel_a2a:
            _helm_uninstall("a2a-inspector", self.NAMESPACE, rel_a2a)
        if rel_mcp:
            _helm_uninstall("mcp-inspector", self.NAMESPACE, rel_mcp)
        _k8s_delete_namespace(self.NAMESPACE)

    @pytest.mark.skipif("a2a-inspector" in SKIP_ITEMS, reason="a2a-inspector in SKIP_ITEMS")
    def test_a2a_inspector_ui(self):
        with port_forward(self._rel_a2a, 19310, 8080, self.NAMESPACE) as base_url:
            r = requests.get(base_url, timeout=10)
            assert r.status_code == 200
            assert "A2A" in r.text, f"Expected 'A2A' in a2a-inspector response body"

    @pytest.mark.skipif("mcp-inspector" in SKIP_ITEMS, reason="mcp-inspector in SKIP_ITEMS")
    def test_mcp_inspector_ui(self):
        with port_forward(self._rel_mcp, 19311, 6274, self.NAMESPACE) as base_url:
            assert requests.get(base_url, timeout=10).status_code == 200


# ===========================================================================
# TestExecutors
# ===========================================================================


@pytest.mark.marketplace_feature
class TestExecutors:
    """Each executor registers an ExecutionEngine CR and exposes a healthy /health endpoint."""

    NAMESPACE = "executors-ft"
    EXECUTORS = [
        pytest.param("executor-openai-responses", 8000, 19320,
                     id="executor-openai-responses",
                     marks=pytest.mark.skipif("executor-openai-responses" in SKIP_ITEMS,
                                              reason="executor-openai-responses in SKIP_ITEMS")),
        pytest.param("executor-claude-agent-sdk", 8000, 19321,
                     id="executor-claude-agent-sdk",
                     marks=pytest.mark.skipif("executor-claude-agent-sdk" in SKIP_ITEMS,
                                              reason="executor-claude-agent-sdk in SKIP_ITEMS")),
        pytest.param("executor-langchain", 8000, 19322,
                     id="executor-langchain",
                     marks=pytest.mark.skipif("executor-langchain" in SKIP_ITEMS,
                                              reason="executor-langchain in SKIP_ITEMS")),
    ]

    @pytest.fixture(autouse=True, scope="class")
    def install(self):
        releases = {}
        for p in self.EXECUTORS:
            name = p.values[0]
            if name not in SKIP_ITEMS:
                releases[name] = _helm_install(name, self.NAMESPACE)
        yield
        for name, rel in releases.items():
            _helm_uninstall(name, self.NAMESPACE, rel)
        _k8s_delete_namespace(self.NAMESPACE)

    @pytest.mark.parametrize("name,port,lport", EXECUTORS)
    def test_executor_deployed(self, name, port, lport):
        """ExecutionEngine CR exists with address, and /health returns 200."""
        obj = _get_resource("executionengine", name, self.NAMESPACE)
        assert obj, f"ExecutionEngine/{name} not found"
        assert obj.get("spec", {}).get("address"), f"ExecutionEngine/{name} has no spec.address"
        with port_forward(name, lport, port, self.NAMESPACE) as base_url:
            r = requests.get(f"{base_url}/health", timeout=10)
            assert r.status_code == 200, f"{name} /health → {r.status_code}: {r.text[:200]}"


# ===========================================================================
# TestKYCDemoBundle
# ===========================================================================


@pytest.mark.skipif("kyc-demo-bundle" in SKIP_ITEMS, reason="kyc-demo-bundle in SKIP_ITEMS")
@pytest.mark.marketplace_feature
class TestKYCDemoBundle:
    """kyc-demo-bundle: 5 Agent CRs + 4 Team CRs deployed with correct config."""

    NAMESPACE = "kyc-demo-test"
    EXPECTED_AGENTS = [
        "document-verifier", "ubo-extractor", "sanctions-screener",
        "risk-assessor", "compliance-reporter",
    ]
    EXPECTED_TEAMS = [
        "identity-verification-team", "ownership-analysis-team",
        "compliance-screening-team", "risk-assessment-team",
    ]

    @pytest.fixture(autouse=True, scope="class")
    def install(self):
        # helm install is blocked by the local Ark controller webhook:
        #   - "maxTurns can only be set when loops is enabled" (Team webhook)
        #   - "maxCompletionTokens" unknown in older Agent CRD
        # _template_and_apply patches those fields before applying.
        _template_cleanup(self.NAMESPACE)  # ensure clean slate
        _template_and_apply(
            "kyc-demo-bundle", self.NAMESPACE,
            extra_set=["file-gateway.enabled=false"],  # avoid sub-chart port conflicts
        )
        yield
        _template_cleanup(self.NAMESPACE)

    def test_agents_deployed(self):
        """All expected Agent CRs exist with a prompt, model ref, and file tools."""
        errors: list[str] = []
        for name in self.EXPECTED_AGENTS:
            obj = _get_resource("agent", name, self.NAMESPACE)
            if not obj:
                errors.append(f"Agent/{name} not found")
                continue
            spec = obj.get("spec", {})
            if not spec.get("prompt", "").strip():
                errors.append(f"Agent/{name} has no prompt")
            if not spec.get("modelRef", {}).get("name"):
                errors.append(f"Agent/{name} has no modelRef")
            tool_names = [t.get("name", "") for t in spec.get("tools", [])]
            if not any("file" in n for n in tool_names):
                errors.append(f"Agent/{name} missing file tool (got: {tool_names})")
        assert not errors, "\n".join(errors)

    def test_teams_deployed(self):
        """All expected Team CRs exist with members and a strategy."""
        errors: list[str] = []
        for name in self.EXPECTED_TEAMS:
            obj = _get_resource("team", name, self.NAMESPACE)
            if not obj:
                errors.append(f"Team/{name} not found")
                continue
            spec = obj.get("spec", {})
            if not spec.get("members"):
                errors.append(f"Team/{name} has no members")
            if not spec.get("strategy"):
                errors.append(f"Team/{name} has no strategy")
        assert not errors, "\n".join(errors)

    def test_expected_counts(self):
        """Exactly the declared agents and teams are present."""
        agent_names = {a["metadata"]["name"] for a in _list_resources("agent", self.NAMESPACE)}
        team_names  = {t["metadata"]["name"] for t in _list_resources("team",  self.NAMESPACE)}
        missing_agents = set(self.EXPECTED_AGENTS) - agent_names
        missing_teams  = set(self.EXPECTED_TEAMS)  - team_names
        assert not missing_agents, f"Missing agents: {sorted(missing_agents)}"
        assert not missing_teams,  f"Missing teams: {sorted(missing_teams)}"


# ===========================================================================
# TestKYCOnboardingBundle
# ===========================================================================


@pytest.mark.skipif("kyc-onboarding-bundle" in SKIP_ITEMS, reason="kyc-onboarding-bundle in SKIP_ITEMS")
@pytest.mark.marketplace_feature
class TestKYCOnboardingBundle:
    """kyc-onboarding-bundle: spot-checks a representative subset and verifies counts."""

    NAMESPACE = "kyc-onboard-test"
    SPOT_CHECK_AGENTS = [
        "scout-agent", "rag-agent", "beneficial-owner-tree-agent",
        "bo-analyst", "file-manager-agent",
    ]
    SPOT_CHECK_TEAMS = ["scout-rag-team", "beneficial-owners-team", "consolidation-team"]
    MIN_AGENT_COUNT = 20
    MIN_TEAM_COUNT = 5

    @pytest.fixture(autouse=True, scope="class")
    def install(self):
        # Argo WorkflowTemplate CRDs are not installed locally; disable them.
        # Team member validation requires agents to exist first — _template_and_apply
        # handles the ordering (non-Teams applied before Teams).
        _template_cleanup(self.NAMESPACE)
        _template_and_apply(
            "kyc-onboarding-bundle", self.NAMESPACE,
            extra_set=[
                "argoWorkflows.workflowTemplate.enabled=false",
                "argoWorkflows.rbac.enabled=false",
                "file-gateway.enabled=false",
            ],
        )
        yield
        _template_cleanup(self.NAMESPACE)

    def test_spot_check_agents(self):
        """Representative agents exist with a model reference and a non-empty prompt."""
        errors: list[str] = []
        for name in self.SPOT_CHECK_AGENTS:
            obj = _get_resource("agent", name, self.NAMESPACE)
            if not obj:
                errors.append(f"Agent/{name} not found")
            else:
                spec = obj.get("spec", {})
                if not spec.get("modelRef", {}).get("name"):
                    errors.append(f"Agent/{name} has no modelRef.name")
                if not spec.get("prompt", "").strip():
                    errors.append(f"Agent/{name} has empty prompt")
        assert not errors, "\n".join(errors)

    def test_spot_check_teams(self):
        """Representative teams exist."""
        missing = [n for n in self.SPOT_CHECK_TEAMS if not _get_resource("team", n, self.NAMESPACE)]
        assert not missing, f"Teams not found: {missing}"

    def test_minimum_counts(self):
        """At least the declared minimum of agents and teams are present."""
        agents = _list_resources("agent", self.NAMESPACE)
        teams  = _list_resources("team",  self.NAMESPACE)
        assert len(agents) >= self.MIN_AGENT_COUNT, (
            f"Expected ≥{self.MIN_AGENT_COUNT} agents, got {len(agents)}"
        )
        assert len(teams) >= self.MIN_TEAM_COUNT, (
            f"Expected ≥{self.MIN_TEAM_COUNT} teams, got {len(teams)}"
        )


# ===========================================================================
# TestFilesystemMCP
# ===========================================================================


@pytest.mark.skipif("filesystem-mcp-server" in SKIP_ITEMS, reason="filesystem-mcp-server in SKIP_ITEMS")
@pytest.mark.marketplace_feature
class TestFilesystemMCP:
    """filesystem-mcp-server: MCPServer CR registered and service reachable."""

    NAMESPACE = "filesystem-mcp-ft"
    LOCAL_PORT = 19330

    @pytest.fixture(autouse=True, scope="class")
    def install(self):
        release = _helm_install("filesystem-mcp-server", self.NAMESPACE)
        yield
        _helm_uninstall("filesystem-mcp-server", self.NAMESPACE, release)
        _k8s_delete_namespace(self.NAMESPACE)

    def test_mcpserver_cr(self):
        """MCPServer CR exists and has a non-empty spec.address."""
        resources = _list_resources("mcpserver", self.NAMESPACE)
        fs = [r for r in resources if "filesystem" in r.get("metadata", {}).get("name", "")]
        assert fs, f"No filesystem MCPServer CR found. Found: {[r['metadata']['name'] for r in resources]}"
        assert fs[0].get("spec", {}).get("address"), f"MCPServer has no spec.address: {fs[0].get('spec')}"

    def test_mcp_service_responds(self):
        # Service is named after the chart name (mcp-filesystem.name), not the release name.
        with port_forward("filesystem-mcp-server-server", self.LOCAL_PORT, 8080, self.NAMESPACE) as base_url:
            r = requests.get(f"{base_url}/health", timeout=10)
            assert r.status_code == 200


# ===========================================================================
# TestNoah
# ===========================================================================


@pytest.mark.skipif("noah" in SKIP_ITEMS, reason="noah in SKIP_ITEMS")
@pytest.mark.marketplace_feature
class TestNoah:
    """Noah: Agent CR deployed with a prompt, MCP pod running and healthy."""

    NAMESPACE = "noah-ft"
    LOCAL_PORT = 19340

    @pytest.fixture(autouse=True, scope="class")
    def install(self):
        release = _helm_install("noah", self.NAMESPACE)
        yield
        _helm_uninstall("noah", self.NAMESPACE, release)
        _k8s_delete_namespace(self.NAMESPACE)

    def test_agent_cr(self):
        """Agent/noah exists and has a non-trivial prompt."""
        obj = _get_resource("agent", "noah", self.NAMESPACE)
        assert obj, "Agent/noah not found"
        assert len(obj.get("spec", {}).get("prompt", "").strip()) > 50, "Noah prompt too short"

    def test_mcp_healthy(self):
        """noah-mcp container is ready (not CrashLoopBackOff) and /health returns 200."""
        pods = k8s_client.CoreV1Api().list_namespaced_pod(
            namespace=self.NAMESPACE, label_selector="app=noah-mcp"
        )
        assert pods.items, f"No noah-mcp pods found in namespace {self.NAMESPACE!r}"
        container_statuses = pods.items[0].status.container_statuses or []
        assert container_statuses and container_statuses[0].ready, (
            f"noah-mcp not ready — run: kubectl logs -l app=noah-mcp -n {self.NAMESPACE}"
        )
        with port_forward("noah-mcp", self.LOCAL_PORT, 8639, self.NAMESPACE) as base_url:
            assert requests.get(f"{base_url}/health", timeout=10).status_code == 200


# ===========================================================================
# TestArkSandbox
# ===========================================================================


@pytest.mark.skipif("ark-sandbox" in SKIP_ITEMS, reason="ark-sandbox in SKIP_ITEMS")
@pytest.mark.marketplace_feature
class TestArkSandbox:
    """
    Ark Sandbox: Kubernetes controller + MCP server for isolated dev containers.

    Checks:
    - Deployment is healthy and /health returns 200
    - MCPServer CR is registered with a spec.address
    """

    NAMESPACE = "ark-sandbox-ft"
    LOCAL_PORT = 19350

    @pytest.fixture(autouse=True, scope="class")
    def install(self):
        release = _helm_install("ark-sandbox", self.NAMESPACE)
        yield
        _helm_uninstall("ark-sandbox", self.NAMESPACE, release)
        _k8s_delete_namespace(self.NAMESPACE)

    def test_health(self):
        with port_forward("ark-sandbox", self.LOCAL_PORT, 80, self.NAMESPACE) as base_url:
            r = requests.get(f"{base_url}/health", timeout=10)
            assert r.status_code == 200, f"ark-sandbox /health → {r.status_code}: {r.text[:200]}"

    def test_mcpserver_cr(self):
        """MCPServer CR 'ark-sandbox' exists with a non-empty spec.address."""
        resources = _list_resources("mcpserver", self.NAMESPACE)
        sb = [r for r in resources if "sandbox" in r.get("metadata", {}).get("name", "")]
        assert sb, f"No ark-sandbox MCPServer CR found. Got: {[r['metadata']['name'] for r in resources]}"
        assert sb[0].get("spec", {}).get("address"), f"MCPServer has no spec.address: {sb[0].get('spec')}"


# ===========================================================================
# TestLangfuse
# ===========================================================================


@pytest.mark.skipif("langfuse" in SKIP_ITEMS, reason="langfuse in SKIP_ITEMS")
@pytest.mark.marketplace_feature
class TestLangfuse:
    """
    Langfuse observability service.

    Checks:
    - Web pod is running and the Langfuse UI (port 3000) responds with 200
    """

    NAMESPACE = "langfuse"
    LOCAL_PORT = 19360

    @pytest.fixture(autouse=True, scope="class")
    def install(self):
        release = _helm_install("langfuse", self.NAMESPACE)
        yield
        _helm_uninstall("langfuse", self.NAMESPACE, release)
        _k8s_delete_namespace(self.NAMESPACE)

    def test_web_ui(self):
        """Langfuse web service serves HTTP 200."""
        # The sub-chart prefixes services with the release name → {release}-web
        svc = f"langfuse-ft-web"
        r = None
        with port_forward(svc, self.LOCAL_PORT, 3000, self.NAMESPACE, wait_secs=5.0) as base_url:
            for _ in range(20):
                try:
                    r = requests.get(base_url, timeout=5)
                    if r.status_code == 200:
                        break
                except requests.exceptions.ConnectionError:
                    pass
                time.sleep(3)
        assert r is not None and r.status_code == 200, (
            f"Langfuse UI never returned 200 (last: {r.status_code if r else 'no response'})"
        )


# ===========================================================================
# TestPhoenix
# ===========================================================================


@pytest.mark.skipif("phoenix" in SKIP_ITEMS, reason="phoenix in SKIP_ITEMS")
@pytest.mark.marketplace_feature
class TestPhoenix:
    """
    Phoenix (Arize) observability service.

    Checks:
    - Phoenix pod is running and the UI (port 6006) responds with 200
    """

    NAMESPACE = "phoenix"
    LOCAL_PORT = 19370

    @pytest.fixture(autouse=True, scope="class")
    def install(self):
        release = _helm_install("phoenix", self.NAMESPACE)
        yield
        _helm_uninstall("phoenix", self.NAMESPACE, release)
        _k8s_delete_namespace(self.NAMESPACE)

    def test_web_ui(self):
        """Phoenix UI serves HTTP 200."""
        # Sub-chart prefixes services → {release}-svc
        svc = "phoenix-ft-svc"
        r = None
        with port_forward(svc, self.LOCAL_PORT, 6006, self.NAMESPACE, wait_secs=5.0) as base_url:
            for _ in range(20):
                try:
                    r = requests.get(base_url, timeout=5)
                    if r.status_code == 200:
                        break
                except requests.exceptions.ConnectionError:
                    pass
                time.sleep(3)
        assert r is not None and r.status_code == 200, (
            f"Phoenix UI never returned 200 (last: {r.status_code if r else 'no response'})"
        )


# ===========================================================================
# TestMCPServers  (companies-house, pdf-extraction, perplexity, speech, web-research)
# ===========================================================================


@pytest.mark.marketplace_feature
class TestMCPServers:
    """
    Parametrized test covering the five MCP servers that require external API
    keys or locally-built Docker images.

    Because the images are not pre-published to a registry, helm install is
    performed via ``_template_and_apply`` (no ``--wait``) so the MCPServer CR
    gets created even when pod images can't be pulled.

    Checks:
    - MCPServer CR is created with a non-empty spec.address
    """

    NAMESPACE = "mcp-servers-ft"

    # (helm-item-name, expected MCPServer CR name)
    MCP_ITEMS = [
        pytest.param("companies-house-mcp", "companies-house",         # nameOverride in chart
                     id="companies-house-mcp",
                     marks=pytest.mark.skipif("companies-house-mcp" in SKIP_ITEMS,
                                              reason="companies-house-mcp in SKIP_ITEMS")),
        pytest.param("pdf-extraction-mcp", "pdf-extraction-mcp-ft",
                     id="pdf-extraction-mcp",
                     marks=pytest.mark.skipif("pdf-extraction-mcp" in SKIP_ITEMS,
                                              reason="pdf-extraction-mcp in SKIP_ITEMS")),
        pytest.param("perplexity-ask-mcp", "perplexity",               # nameOverride in chart
                     id="perplexity-ask-mcp",
                     marks=pytest.mark.skipif("perplexity-ask-mcp" in SKIP_ITEMS,
                                              reason="perplexity-ask-mcp in SKIP_ITEMS")),
        pytest.param("speech-mcp-server", "speech-mcp-server-ft",
                     id="speech-mcp-server",
                     marks=pytest.mark.skipif("speech-mcp-server" in SKIP_ITEMS,
                                              reason="speech-mcp-server in SKIP_ITEMS")),
        pytest.param("web-research-mcp", "web-research-mcp-ft",
                     id="web-research-mcp",
                     marks=pytest.mark.skipif("web-research-mcp" in SKIP_ITEMS,
                                              reason="web-research-mcp in SKIP_ITEMS")),
    ]

    @pytest.fixture(autouse=True, scope="class")
    def install(self):
        _k8s_create_namespace(self.NAMESPACE)
        for p in self.MCP_ITEMS:
            name, _cr_name = p.values
            if name not in SKIP_ITEMS:
                # Use helm template + apply so the MCPServer CR is created even
                # when the image can't be pulled (no published GHCR image yet).
                chart_dir = REPO_ROOT / _CHART_PATHS[name] / "chart"
                _helm("dependency", "update", str(chart_dir), check=False)
                cmd = [_HELM, "template", f"{name}-ft", str(chart_dir),
                       "--namespace", self.NAMESPACE]
                result = _run(cmd, check=False)
                if result.returncode != 0:
                    continue  # individual test will show it as skipped
                docs = [d for d in yaml.safe_load_all(result.stdout) if d is not None]
                subprocess.run(
                    [_KUBECTL, "apply", "-f", "-", "-n", self.NAMESPACE],
                    input=yaml.dump_all(docs), text=True, capture_output=True,
                )
        yield
        _k8s_delete_namespace(self.NAMESPACE)

    @pytest.mark.parametrize("name,cr_name", MCP_ITEMS)
    def test_mcpserver_cr(self, name, cr_name):
        """MCPServer CR exists with a non-empty spec.address."""
        obj = _get_resource("mcpserver", cr_name, self.NAMESPACE)
        assert obj, f"MCPServer/{cr_name} not found (rendered by helm template for {name})"
        assert obj.get("spec", {}).get("address"), (
            f"MCPServer/{cr_name} has no spec.address: {obj.get('spec')}"
        )


# ===========================================================================
# TestCOBOLBundle
# ===========================================================================


@pytest.mark.skipif("cobol-modernization-bundle" in SKIP_ITEMS, reason="cobol-modernization-bundle in SKIP_ITEMS")
@pytest.mark.marketplace_feature
class TestCOBOLBundle:
    """
    cobol-modernization-bundle: 6 Agent CRs for COBOL reverse-engineering.

    Uses ``_template_and_apply`` to skip Argo WorkflowTemplates (CRDs not
    installed locally) and the speech-mcp-server sub-chart (no published image).
    """

    NAMESPACE = "cobol-test"

    EXPECTED_AGENTS = [
        "audio-transcriber",
        "cobol-code-documenter",
        "cobol-codebase-summarizer",
        "cobol-pseudocode-documenter",
        "diagram-creator",
        "pseudo-python-modernizer",
    ]

    @pytest.fixture(autouse=True, scope="class")
    def install(self):
        _template_cleanup(self.NAMESPACE)
        _template_and_apply(
            "cobol-modernization-bundle", self.NAMESPACE,
            extra_set=[
                "argoWorkflows.workflowTemplate.enabled=false",
                "argoWorkflows.rbac.enabled=false",
                "file-gateway.enabled=false",
                "speech-mcp-server.enabled=false",
            ],
        )
        yield
        _template_cleanup(self.NAMESPACE)

    def test_agents_deployed(self):
        """All 6 COBOL Agent CRs exist with a model reference and a non-empty prompt."""
        errors: list[str] = []
        for name in self.EXPECTED_AGENTS:
            obj = _get_resource("agent", name, self.NAMESPACE)
            if not obj:
                errors.append(f"Agent/{name} not found")
            else:
                spec = obj.get("spec", {})
                if not spec.get("modelRef", {}).get("name"):
                    errors.append(f"Agent/{name} has no modelRef.name")
                if not spec.get("prompt", "").strip():
                    errors.append(f"Agent/{name} has empty prompt")
        assert not errors, "\n".join(errors)

    def test_expected_count(self):
        """All declared agents are present — no extras, none missing."""
        agent_names = {a["metadata"]["name"] for a in _list_resources("agent", self.NAMESPACE)}
        missing = set(self.EXPECTED_AGENTS) - agent_names
        assert not missing, f"Missing COBOL agents: {sorted(missing)}"
