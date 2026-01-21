# Executor Claude Agent

ARK ExecutionEngine implementation using Claude Agent SDK for agentic task execution.

## Overview

This executor enables ARK to use Claude models (via Anthropic API or AWS Bedrock) as a native execution engine. Agents created with this executor can leverage Claude's capabilities for code generation, analysis, and multi-turn conversations.

## Features

- **Dual Provider Support**: Works with both Anthropic API and AWS Bedrock
- **ARK Native**: Implements the ExecutionEngine protocol for seamless integration
- **Agentic Capabilities**: Supports Claude Agent SDK for tool use and multi-turn execution
- **OpenTelemetry**: Built-in observability support

## Installation

### Via Helm

```bash
helm install executor-claude-agent oci://ghcr.io/mckinsey/agents-at-scale-marketplace/charts/executor-claude-agent
```

### Via ARK CLI

```bash
ark marketplace install executor-claude-agent
```

## Configuration

### Using Anthropic API

Create a secret with your API key:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: anthropic-credentials
type: Opaque
stringData:
  api-key: "your-api-key"
```

Configure in values:

```yaml
anthropicApiKey:
  existingSecret: "anthropic-credentials"
  existingSecretKey: "api-key"
```

### Using AWS Bedrock

Create a secret with AWS credentials:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: aws-bedrock-credentials
type: Opaque
stringData:
  AWS_ACCESS_KEY_ID: "your-access-key"
  AWS_SECRET_ACCESS_KEY: "your-secret-key"
  AWS_SESSION_TOKEN: "optional-session-token"
  AWS_REGION: "us-east-1"
```

The executor auto-detects Bedrock when AWS credentials are present and no Anthropic API key is configured.

## Creating Agents

Once the executor is installed, create agents that use it:

```yaml
apiVersion: ark.mckinsey.com/v1alpha1
kind: Model
metadata:
  name: claude-bedrock
spec:
  type: bedrock
  model:
    value: "us.anthropic.claude-3-5-sonnet-20241022-v2:0"
  config:
    bedrock:
      region:
        value: "us-east-1"
      accessKeyId:
        valueFrom:
          secretKeyRef:
            name: aws-bedrock-credentials
            key: AWS_ACCESS_KEY_ID
      secretAccessKey:
        valueFrom:
          secretKeyRef:
            name: aws-bedrock-credentials
            key: AWS_SECRET_ACCESS_KEY
---
apiVersion: ark.mckinsey.com/v1alpha1
kind: Agent
metadata:
  name: claude-developer
spec:
  description: "Expert Python developer agent"
  executionEngine:
    name: executor-claude-agent
  modelRef:
    name: claude-bedrock
  prompt: |
    You are an expert Python developer. Write clean, well-documented code.
    Follow best practices and provide explanations for your implementations.
```

## Querying Agents

```yaml
apiVersion: ark.mckinsey.com/v1alpha1
kind: Query
metadata:
  name: my-query
spec:
  type: user
  input: "Write a function to calculate fibonacci numbers"
  targets:
    - name: claude-developer
      type: agent
```

## Supported Models

| Model Name | Bedrock Model ID |
|------------|------------------|
| claude-sonnet-4-20250514 | us.anthropic.claude-sonnet-4-20250514-v1:0 |
| claude-3-5-sonnet | us.anthropic.claude-3-5-sonnet-20241022-v2:0 |
| claude-3-sonnet | us.anthropic.claude-3-sonnet-20240229-v1:0 |
| claude-3-haiku | us.anthropic.claude-3-haiku-20240307-v1:0 |
| claude-3-opus | us.anthropic.claude-3-opus-20240229-v1:0 |

## Integration with ARK Sandbox

The executor-claude-agent is stateless by design. For file operations and code execution capabilities, integrate with [ark-sandbox](../ark-sandbox/).

### Prerequisites

Install both services:

```bash
ark marketplace install ark-sandbox
ark marketplace install executor-claude-agent
```

### Creating an Agent with Sandbox Access

Create an agent that references both the executor and the ark-sandbox MCP server:

```yaml
apiVersion: ark.mckinsey.com/v1alpha1
kind: Agent
metadata:
  name: claude-developer-with-sandbox
spec:
  description: "Claude developer with file and code execution capabilities"
  executionEngine:
    name: executor-claude-agent
  modelRef:
    name: claude-bedrock
  mcpServers:
    - name: ark-sandbox
  prompt: |
    You are an expert developer with access to sandbox tools.

    Available tools:
    - create_sandbox: Create an isolated container environment
    - execute_command: Run shell commands in the sandbox
    - upload_file: Write files to the sandbox
    - download_file: Read files from the sandbox
    - get_sandbox_logs: View container logs
    - delete_sandbox: Clean up when done

    Always create a sandbox before executing code, and clean up after.
```

### Sandbox Tools Reference

| Tool | Description | Key Parameters |
|------|-------------|----------------|
| `create_sandbox` | Create isolated container | `image`, `ttl_minutes`, `pvc_name` |
| `execute_command` | Run shell commands | `sandbox_id`, `command`, `working_dir` |
| `upload_file` | Write file to sandbox | `sandbox_id`, `path`, `content` |
| `download_file` | Read file from sandbox | `sandbox_id`, `path` |
| `get_sandbox_logs` | Get container logs | `sandbox_id`, `tail_lines` |
| `delete_sandbox` | Remove sandbox | `sandbox_id` |
| `list_sandboxes` | List all sandboxes | `namespace` |
| `claim_sandbox_from_pool` | Get pre-warmed sandbox | `pool_name` |

### Using Shared Storage (PVC)

For workflows that need persistent storage across sandbox sessions:

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: workflow-storage
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 10Gi
---
apiVersion: ark.mckinsey.com/v1alpha1
kind: Query
metadata:
  name: code-task
spec:
  type: user
  input: |
    Create a sandbox with the workflow-storage PVC mounted.
    Write a Python script to /shared/analysis.py that processes data.
    Execute it and save results to /shared/results.json.
  targets:
    - name: claude-developer-with-sandbox
      type: agent
```

The PVC will be mounted at `/shared` in the sandbox, allowing data persistence.

### Warm Pools for Fast Startup

Pre-create sandboxes for instant availability:

```yaml
apiVersion: ark.mckinsey.com/v1alpha1
kind: SandboxTemplate
metadata:
  name: python-dev
spec:
  image: python:3.13-slim
  ttlMinutes: 120
  resources:
    limits:
      cpu: "2"
      memory: "4Gi"
---
apiVersion: ark.mckinsey.com/v1alpha1
kind: SandboxPool
metadata:
  name: python-pool
spec:
  templateRef:
    name: python-dev
  minSize: 3
  maxSize: 10
```

Then use `claim_sandbox_from_pool` instead of `create_sandbox` for faster startup.

### Architecture with Sandbox

```
                                    ┌─────────────────┐
                                    │   ark-sandbox   │
                                    │   (MCP Server)  │
                                    └────────▲────────┘
                                             │ MCP tools
┌───────┐    ┌───────┐    ┌─────────────────┴────────────────┐    ┌──────────┐
│ Query │───►│ Agent │───►│ executor-claude-agent            │───►│ Bedrock/ │
└───────┘    └───────┘    │ (ExecutionEngine)                │    │ Anthropic│
                          └──────────────────────────────────┘    └──────────┘
```

The executor receives tool definitions from ARK, calls Claude, and Claude can invoke sandbox tools through ARK's MCP integration.

## Architecture

```
ARK Query → Agent → ExecutionEngine (executor-claude-agent) → Bedrock/Anthropic API → Response
```

The executor:
1. Receives requests from ARK's broker
2. Translates to Claude's message format
3. Calls the appropriate provider (Bedrock or Anthropic)
4. Returns responses in ARK's format

## Values Reference

| Parameter | Description | Default |
|-----------|-------------|---------|
| `image.repository` | Docker image repository | `ghcr.io/mckinsey/executor-claude-agent` |
| `image.tag` | Docker image tag | `""` (uses appVersion) |
| `claude.model` | Default Claude model | `claude-sonnet-4-20250514` |
| `claude.maxTurns` | Max agentic turns | `10` |
| `anthropicApiKey.existingSecret` | Secret name for API key | `""` |
| `otel.enabled` | Enable OpenTelemetry | `false` |
| `executionEngine.enabled` | Create ExecutionEngine CRD | `true` |
| `executionEngine.name` | ExecutionEngine name | `executor-claude-agent` |

## License

Apache-2.0
