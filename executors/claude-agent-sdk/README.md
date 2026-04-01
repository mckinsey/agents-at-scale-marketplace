# Claude Agent SDK Executor

Native Claude executor for the ARK platform, built on the [Claude Agent SDK](https://platform.claude.com/docs/en/agent-sdk/overview). Provides built-in tool access (Read, Write, Edit, Bash, Grep, Glob) with per-session filesystem isolation and optional OTEL tracing.

## Quick Start

```bash
# Using ARK CLI
ark install marketplace/executors/executor-claude-agent-sdk

# Using DevSpace
cd executors/claude-agent-sdk
devspace deploy

# Using Helm
helm install executor-claude-agent-sdk ./chart -n default --create-namespace
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
    value: claude-sonnet-4-20250514
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

## How It Works

- Each `conversationId` gets an isolated directory at `/data/sessions/<conversationId>/`
- The Claude Agent SDK's built-in tools operate within that directory
- Sessions persist across requests via `ClaudeSDKClient` with `continue_conversation`
- Session data survives pod restarts via a PersistentVolumeClaim

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
