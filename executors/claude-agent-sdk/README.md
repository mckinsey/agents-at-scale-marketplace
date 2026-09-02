# Claude Agent SDK Executor

Native Claude executor for the Ark platform, built on the [Claude Agent SDK](https://platform.claude.com/docs/en/agent-sdk/overview). Provides built-in tool access (Read, Write, Edit, Bash, Grep, Glob) with per-session filesystem isolation and optional OTEL tracing.

Two deployment modes:
- **Standalone** (default in Helm) — single executor pod with PVC for session persistence
- **Scheduler** (default in DevSpace) — per-conversation sandbox pods via [agent-sandbox](https://github.com/kubernetes-sigs/agent-sandbox), providing full container-level isolation

## Quick Start

```bash
# Using Ark CLI
ark install marketplace/executors/executor-claude-agent-sdk

# Using DevSpace (scheduler mode by default)
cd executors/claude-agent-sdk
devspace deploy

# Using DevSpace (standalone mode)
devspace deploy -p standalone

# Using Helm (standalone by default)
helm install executor-claude-agent-sdk ./chart -n default --create-namespace

# Using Helm (scheduler mode)
helm install executor-claude-agent-sdk ./chart -n default --create-namespace --set scheduler.enabled=true
```

## Prerequisites

Create a Model CRD with your Anthropic configuration:

```yaml
apiVersion: ark.mckinsey.com/v1alpha1
kind: Model
metadata:
  name: claude-sonnet
spec:
  model:
    value: claude-sonnet-4-6
  provider: anthropic
  config:
    anthropic:
      baseUrl:
        value: my-base-url
      apiKey:
        valueFrom:
          secretKeyRef:
            name: my-anthropic-secret
            key: api-key
```

Reference the Model from your Agent CRD via `spec.model.ref: claude-sonnet`.

Optionally enable OTEL tracing:

```bash
kubectl create secret generic otel-environment-variables \
  --from-literal=OTEL_EXPORTER_OTLP_ENDPOINT=<endpoint> \
  --from-literal=OTEL_EXPORTER_OTLP_HEADERS='Authorization=Bearer <token>'
```

## Creating Agents

```yaml
apiVersion: ark.mckinsey.com/v1alpha1
kind: Agent
metadata:
  name: my-claude-agent
spec:
  executionEngine:
    name: executor-claude-agent-sdk
  modelRef:
    name: claude-sonnet
  prompt: |
    You are a helpful assistant with access to filesystem tools.
```

## Teams

Agents on this executor can be members of a `Team`. Ark dispatches each member to its
execution engine and names the member in the query extension metadata, so a member runs
with the team transcript so far and its own conversation scope — one session directory per
member, not one shared across the team.

```yaml
apiVersion: ark.mckinsey.com/v1alpha1
kind: Team
metadata:
  name: my-team
spec:
  strategy: sequential
  members:
    - type: agent
      name: writer
    - type: agent
      name: reviewer
```

The calling engine owns the parent Query's status, stream, and memory for the whole run.
A member call writes none of them, and human-in-the-loop approval is not available to a
member — the member's engine cannot resume an approval the caller owns.

Requires both an Ark version that sends the query extension `target` field and an executor
image built against an ark-sdk that reads it. An older Ark never dispatches a member to its
engine, so the member runs on the completions loop instead. A newer Ark against an older
ark-sdk fails the member call with `Query extension resolution only supports agent targets,
got 'team'`.

In scheduler mode each member turn provisions its own sandbox, because member calls carry
no `contextId`. `scheduler.config.maxActiveSandboxes` defaults to `0` (unlimited); if you
have capped it, a 3-member sequential team needs 3 and a selector team needs up to two per
turn.

## Deployment Modes

### Standalone

The executor runs as a single long-lived pod. All conversations share one process. Session data persists on a PVC at `/data/sessions/<conversationId>/`.

### Scheduler (sandbox isolation)

A scheduler proxy sits in front, creating an ephemeral [agent-sandbox](https://github.com/kubernetes-sigs/agent-sandbox) pod per conversation. Each sandbox runs the unchanged executor image with full container-level isolation (process, filesystem, environment).

**Prerequisites** — install the agent-sandbox controller (core + extensions):

```bash
VERSION=v0.2.1
kubectl apply -f https://github.com/kubernetes-sigs/agent-sandbox/releases/download/${VERSION}/manifest.yaml
kubectl apply -f https://github.com/kubernetes-sigs/agent-sandbox/releases/download/${VERSION}/extensions.yaml
```

**How it works:**
- The scheduler extracts `contextId` from A2A messages and routes to the correct sandbox
- Routing state is stored on SandboxClaim labels/annotations (K8s-native, survives restarts)
- Idle sessions are reaped after `sessionIdleTTL` (default 30 minutes)
- Optional warm pool pre-creates sandbox pods for faster first-message latency

**Session identity:** The scheduler owns session identity. For new conversations, omit `conversationId` from the Query — the scheduler generates a UUID4 and injects it. Use the returned `status.conversationId` for follow-up queries. Non-UUID4 values are rejected.

### Scheduler Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `scheduler.enabled` | Enable scheduler mode | `false` |
| `scheduler.config.sessionIdleTTL` | Idle session timeout (seconds) | `1800` |
| `scheduler.config.shutdownPolicy` | `Delete` or `Retain` expired sandboxes | `Delete` |
| `scheduler.config.sandboxReadyTimeout` | Sandbox readiness timeout (seconds) | `60` |
| `scheduler.config.maxActiveSandboxes` | Max concurrent sandbox pods (0 = unlimited) | `0` |
| `scheduler.warmPool.enabled` | Enable pre-warmed sandbox pool | `false` |
| `scheduler.warmPool.replicas` | Number of warm pool pods | `2` |

### Known Limitations

- **No streaming support**: The proxy buffers the full upstream response before relaying. A2A `message/stream` (SSE) is not supported; use `message/send` only.

## Network Policy

Executor egress is restricted by default in both deployment modes. Standalone pods get a
NetworkPolicy from this chart; sandbox pods get one from the agent-sandbox controller via the
SandboxTemplate. Everything not listed below is denied — other namespaces, the cloud metadata
server, and every port except those named.

| Allowed egress | Notes |
|----------------|-------|
| DNS | CoreDNS in `kube-system`, TCP+UDP 53 |
| Kubernetes API | Resolves Agent, Model, Tool, MCPServer and Secret. Address read from the cluster |
| OTEL collector | Read from the `otel-environment-variables` secret |
| Public internet, TCP 443 | Anthropic API, WebFetch, git. Private ranges and the metadata server stay blocked |
| Pods in this namespace | ark-broker, co-located MCP servers |
| Namespaces labelled `ark.mckinsey.com/executor-egress=allowed` | Cross-namespace targets |

Sandbox pods additionally accept ingress only from the scheduler on port 8000. The standalone
policy restricts egress only and leaves ingress untouched.

### Configuration

No configuration is needed for the common case. The Kubernetes API address and the OTEL endpoint
are both read from the cluster at install time.

To reach an MCP server or other service in another namespace, label that namespace:

```bash
kubectl label namespace <ns> ark.mckinsey.com/executor-egress=allowed
```

| Parameter | Description | Default |
|-----------|-------------|---------|
| `networkPolicy.enabled` | Restrict egress. `false` restores unrestricted egress | `true` |
| `networkPolicy.internetPorts` | Public internet ports. `[]` blocks the internet entirely | `[443]` |
| `networkPolicy.allowSameNamespace` | Allow egress within this namespace | `true` |
| `networkPolicy.allowNamespaces` | Namespaces to allow whose labels you cannot set | `[]` |
| `networkPolicy.autoDetect` | Read the API server address and OTEL endpoint from the cluster while rendering | `true` |
| `networkPolicy.apiServerCIDRs` | API server addresses. Read from the cluster when empty | `[]` |
| `networkPolicy.apiServerPorts` | API server ports. Read from the cluster when empty | `[]` |
| `networkPolicy.extraEgress` | Extra egress rules, appended verbatim | `[]` |
| `networkPolicy.extraIngress` | Extra sandbox ingress rules | `[]` |

### Upgrading an existing install

Upgrading turns egress from unrestricted into default-deny. For most installs there is nothing to
do — the API server address and the tracing endpoint are read from the cluster. Run these checks
first to confirm; both are cheap, so run them regardless of which CNI you use.

```bash
NS=default   # the executor's namespace

# 1. NodeLocal DNSCache - the only severe case
kubectl get ds -n kube-system node-local-dns >/dev/null 2>&1 \
  && echo "PRESENT - add extraEgress before upgrading" || echo "fine"

# 2. MCP servers outside $NS
kubectl get mcpservers -A --no-headers \
  -o custom-columns=NS:.metadata.namespace,NAME:.metadata.name,ADDR:.spec.address.value \
  | awk -v ns=$NS '$1!=ns {print "label needed: " $1}'

# 3. Tracing endpoint - detected automatically, shown for information
kubectl get secret otel-environment-variables -n $NS \
  -o jsonpath='{.data.OTEL_EXPORTER_OTLP_ENDPOINT}' 2>/dev/null | base64 -d
```

Whether the policy has any effect depends on your cluster enforcing NetworkPolicy, which is a
property of the CNI and, on managed platforms, of how it was provisioned — consult your provider's
documentation rather than guessing from what runs in `kube-system`. To settle it empirically, apply
a deny-all egress policy to a scratch pod and see whether traffic stops:

```bash
kubectl create ns np-probe
kubectl -n np-probe run probe --image=curlimages/curl:latest --command -- sleep 300
kubectl -n np-probe wait --for=condition=Ready pod/probe --timeout=120s
kubectl -n np-probe apply -f - <<'EOF'
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata: {name: deny-egress}
spec:
  podSelector: {}
  policyTypes: [Egress]
EOF
# blocked => NetworkPolicy is enforced; 200 => it is not
kubectl -n np-probe exec probe -- curl -s -m 5 -o /dev/null -w "%{http_code}\n" https://example.com
kubectl delete ns np-probe
```

| Check result | Action |
|--------------|--------|
| NodeLocal DNSCache present | Add `extraEgress` for UDP+TCP 53 to `169.254.20.10/32` **before** upgrading, or DNS stops working |
| An MCP server outside the executor's namespace | `kubectl label namespace <ns> ark.mckinsey.com/executor-egress=allowed` |
| Agents use git over SSH or plain HTTP | Add those ports to `extraEgress` |

Then upgrade and run one query. A successful answer is the verification. The policy applies to
running pods immediately, with no restart, so `--set networkPolicy.enabled=false` reverts just as
fast if something was missed.

### Installing without cluster read permissions

Rendering reads the API server address and the tracing endpoint from the cluster, which needs:

| Resource | Namespace | Verb |
|----------|-----------|------|
| `services` (`kubernetes`) | `default` | `get` |
| `endpointslices.discovery.k8s.io` | `default` | `list` |
| `endpoints` (`kubernetes`) | `default` | `get` |
| `secrets` (`otel-environment-variables`) | release namespace | `get` |

The EndpointSlice read is a list rather than a get, because the slice is selected by its
`kubernetes.io/service-name` label. Helm turns any denied read into a render error rather than an
empty result, so an installer without these cannot render the chart with detection on. Turn it off
and supply the addresses:

```yaml
networkPolicy:
  autoDetect: false
  apiServerCIDRs: ["10.96.0.1/32", "<control-plane-ip>/32"]
  apiServerPorts: [443, 6443]
  extraEgress: []   # add a rule here if the OTEL collector is in another namespace
```

With `autoDetect: false` and no addresses supplied, the API server rule falls back to the private
IPv4 ranges plus IPv6 ULA space (`fc00::/7`) on ports 443, 6443 and 8443. That covers single-stack
clusters of either family, but is broader than naming the address — and an API server reached over a
globally routable address is not covered at all, so set `apiServerCIDRs` in that case.

### Caveats

- **The policy only takes effect if your cluster enforces NetworkPolicy.** Plain minikube does not.
  Support depends on the CNI and how the cluster was provisioned; check your provider's docs, or use
  the deny-all probe above to confirm.
- **HTTPS egress to arbitrary hosts stays open**, because NetworkPolicy matches IP addresses and
  cannot distinguish the Anthropic API from any other host. This narrows exfiltration, it does not
  stop it. For a closed posture, serve the model in-cluster via the Model CRD `baseUrl` and set
  `internetPorts: []`.
- **Installing Phoenix or Langfuse after the executor** needs `helm upgrade` on the executor to pick
  up the new endpoint — the same reason Phoenix asks you to restart its consumers.
- **NodeLocal DNSCache** is not matched by the CoreDNS rule; add it via `extraEgress`.
- **Cilium clusters should verify API access after upgrading.** Cilium matches CIDR rules against
  cluster-external destinations and provides a dedicated `kube-apiserver` entity for this case, so
  an `ipBlock` rule may not behave as it does on Calico. If API calls fail, express API server
  egress with a CiliumNetworkPolicy using `toEntities: kube-apiserver`.
- **Renders with no cluster access** — CI, GitOps — cannot auto-detect the API server, and fall back
  to the private IPv4 ranges plus IPv6 ULA space on ports 443, 6443 and 8443. Set `apiServerCIDRs`
  and `apiServerPorts` to narrow that to a single address, or if the API server is reached over a
  globally routable address, which the fallback does not cover.

## How It Works

- Each `conversationId` gets an isolated directory at `/data/sessions/<conversationId>/`
- The Claude Agent SDK's built-in tools operate within that directory
- Sessions resume across requests via `ClaudeSDKClient` with explicit session ID
- In standalone mode, session data survives pod restarts via a PersistentVolumeClaim
- In scheduler mode, session data lives on the sandbox pod's ephemeral filesystem for the conversation lifetime
- For new conversations, omit `conversationId` — the scheduler generates one. Reuse the returned value from `Query.status.conversationId` for follow-ups.

## MCP Tools

Agents can reference MCP-type tools, and the executor will connect to the backing MCP servers alongside its built-in tools. The tool list per server acts as an allowlist — only referenced tools are available to the agent.

```yaml
apiVersion: ark.mckinsey.com/v1alpha1
kind: Agent
metadata:
  name: my-claude-agent
spec:
  executionEngine:
    name: executor-claude-agent-sdk
  prompt: |
    You are a helpful assistant with access to GitHub.
  tools:
    - name: github-mcp-search-repos
    - name: github-mcp-create-issue
```

The executor maps each MCPServer's resolved connection info (url, transport, headers) into the Claude Agent SDK's native `mcp_servers` option. Built-in tools (Read, Write, Edit, Bash, Grep, Glob) remain available.

## Agent Prompt

The `spec.prompt` field from the Agent CRD is passed to the Claude subprocess as appended system instructions. The SDK's built-in system prompt (tool instructions, safety guidelines) is preserved — the agent prompt is appended after it using the `claude_code` preset.

If no prompt is set on the Agent CRD, the executor uses the SDK's default system prompt.

Parameter templating (e.g., `{language}` replaced by a query parameter value) is resolved upstream by the ark-sdk before reaching the executor.

## Configuration

Model name and API key are configured via the Model CRD (see [Prerequisites](#prerequisites)). The following environment variables are available for optional configuration:

| Variable | Description | Default |
|----------|-------------|---------|
| `OTEL_EXPORTER_OTLP_ENDPOINT` | OTLP endpoint for tracing | Disabled |
| `OTEL_EXPORTER_OTLP_HEADERS` | OTLP auth headers | None |

## Credential Injection

The executor supports injecting credentials from Kubernetes Secrets as environment variables into Claude Code sessions. This enables agents to authenticate with external services like GitHub, Git, or APIs.

### Setup

1. Create a Kubernetes Secret with your credentials:

```bash
kubectl create secret generic github-credentials \
  --from-literal=GITHUB_TOKEN=ghp_xxxxxxxxxxxxx
```

2. Configure the executor to load the secret via `extraEnvFrom` in your Helm values:

```yaml
# values.yaml or --set flag
extraEnvFrom:
  - secretRef:
      name: github-credentials
```

3. Deploy or upgrade the executor:

```bash
helm upgrade executor-claude-agent-sdk ./chart \
  --set 'extraEnvFrom[0].secretRef.name=github-credentials'
```

### How It Works

- Environment variables from the executor pod (including those loaded from Secrets via `extraEnvFrom`) are forwarded to the Claude Code subprocess
- Tools like `gh`, `git`, and `curl` automatically discover credentials from the environment
- Credentials are scoped per-deployment — all agents using this executor instance share the same credentials

### Example: GitHub Authentication

```bash
# Create secret with GitHub token
kubectl create secret generic github-credentials \
  --from-literal=GITHUB_TOKEN=ghp_xxxxxxxxxxxxx

# Install executor with credentials
helm install executor-claude-agent-sdk ./chart \
  --set 'extraEnvFrom[0].secretRef.name=github-credentials'

# Create an agent that uses gh CLI
kubectl apply -f - <<EOF
apiVersion: ark.mckinsey.com/v1alpha1
kind: Agent
metadata:
  name: github-agent
spec:
  executionEngine:
    name: executor-claude-agent-sdk
  modelRef:
    name: claude-sonnet
  prompt: |
    You are a GitHub automation assistant.
    Use the gh CLI to interact with repositories.
EOF

# Query the agent
ark query agent/github-agent "Create a PR in myorg/myrepo with title 'Update README'"
```

The agent will now have access to `GITHUB_TOKEN` and can use `gh` CLI commands that require authentication.

### Multiple Secrets

You can inject multiple secrets by adding more entries to `extraEnvFrom`:

```yaml
extraEnvFrom:
  - secretRef:
      name: github-credentials
  - secretRef:
      name: jira-credentials
  - secretRef:
      name: slack-credentials
```

### Security Notes

- Credentials are scoped at the **executor deployment level**, not per-agent
- If you need different credentials for different agents, deploy multiple executor instances
- Use Kubernetes RBAC to control which service accounts can read which Secrets
- Use fine-grained tokens (e.g., GitHub PATs with minimal scope) rather than broad credentials
