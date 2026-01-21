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
