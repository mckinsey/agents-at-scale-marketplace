## Why

The marketplace currently only offers a LangChain-based executor, which routes through LangChain abstractions even when agents target Anthropic models directly. A native Claude executor using the Claude Agent SDK provides a lighter-weight alternative with access to built-in tools (Read, Write, Edit, Bash, Grep, Glob) running on the executor's local filesystem — enabling agents that can autonomously work with files and run commands without custom tool definitions.

## What Changes

- New executor `executor-claude-agent-sdk` under `executors/claude-agent-sdk/`
- Uses `ClaudeSDKClient` from `claude-agent-sdk` for multi-turn sessions with `resume` support
- Each `conversationId` maps to a dedicated session directory on a PVC (`/data/sessions/<conversationId>/`), scoping the SDK's built-in filesystem tools per session
- OTEL tracing via `openinference-instrumentation-claude-agent-sdk`, conditionally enabled when `OTEL_EXPORTER_OTLP_ENDPOINT` is set (loaded from `otel-environment-variables` secret, matching the ark pattern)
- Anthropic API key and model loaded from environment variables (K8s secrets)
- Helm chart with PVC, secret refs, ExecutionEngine CRD registration, RBAC, and optional HTTPRoute
- Marketplace entry, CI/CD matrix entries, release-please config, and documentation

## Capabilities

### New Capabilities
- `claude-agent-execution`: Core executor logic — session management via ClaudeSDKClient, conversationId-to-session mapping, filesystem-scoped tool access, and response collection
- `claude-agent-observability`: Conditional OTEL instrumentation using openinference, wired to the otel-environment-variables secret pattern

### Modified Capabilities

_None — this is a new executor with no changes to existing capabilities._

## Impact

- **New files**: Full executor under `executors/claude-agent-sdk/` (source, Dockerfile, Helm chart, devspace.yaml, pyproject.toml)
- **New docs**: `docs/content/executors/claude-agent-sdk.mdx`
- **Modified files**: `marketplace.json`, `docs/content/executors/_meta.js`, `.github/workflows/main-push.yaml`, `.github/workflows/pull-request.yaml`, `.github/release-please-config.json`, `.github/release-please-manifest.json`
- **Dependencies**: `claude-agent-sdk`, `openinference-instrumentation-claude-agent-sdk`, `opentelemetry-sdk`, `opentelemetry-exporter-otlp`, `ark-sdk`, `a2a-sdk`
- **Infrastructure**: Requires PVC for session persistence; requires `anthropic-api-key` K8s secret; optionally consumes `otel-environment-variables` secret
