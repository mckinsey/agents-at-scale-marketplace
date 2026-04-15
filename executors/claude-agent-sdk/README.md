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
apiVersion: ark.mckinsey.com/v1
kind: Model
metadata:
  name: claude-sonnet
spec:
  model:
    value: claude-sonnet-4-6
  type: anthropic
  config:
    anthropic:
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
  model:
    ref: claude-sonnet
  prompt: |
    You are a helpful assistant with access to filesystem tools.
```

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

## Configuration

Model name and API key are configured via the Model CRD (see [Prerequisites](#prerequisites)). The following environment variables are available for optional configuration:

| Variable | Description | Default |
|----------|-------------|---------|
| `OTEL_EXPORTER_OTLP_ENDPOINT` | OTLP endpoint for tracing | Disabled |
| `OTEL_EXPORTER_OTLP_HEADERS` | OTLP auth headers | None |
