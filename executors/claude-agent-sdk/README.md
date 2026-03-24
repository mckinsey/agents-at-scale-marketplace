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

Create the Anthropic API key secret:

```bash
kubectl create secret generic anthropic-api-key \
  --from-literal=ANTHROPIC_API_KEY=<your-key>
```

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

| Variable | Description | Default |
|----------|-------------|---------|
| `ANTHROPIC_API_KEY` | Anthropic API key (from secret) | Required |
| `ANTHROPIC_MODEL` | Claude model to use | `claude-sonnet-4-20250514` |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | OTLP endpoint for tracing | Disabled |
| `OTEL_EXPORTER_OTLP_HEADERS` | OTLP auth headers | None |
