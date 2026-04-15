## Why

The Claude Agent SDK executor currently runs as a single long-lived pod where all agent sessions share one process and filesystem namespace. Session isolation is limited to per-conversation directories under `/data/sessions/`. The Bash tool, environment variables, and process space are shared across all concurrent sessions, creating security and resource isolation concerns for multi-tenant deployments.

## What Changes

- Introduce a **scheduler** component that receives A2A messages from the Ark controller and manages ephemeral sandbox pods for each conversation, using the [kubernetes-sigs/agent-sandbox](https://github.com/kubernetes-sigs/agent-sandbox) project
- Each conversation gets its own `Sandbox` pod running the **unchanged** Claude Agent SDK executor image, providing full container-level isolation
- The scheduler acts as a transparent A2A HTTP proxy: it extracts `context_id` (conversation ID) from incoming A2A messages, resolves or creates a sandbox for that conversation, and forwards the request to the sandbox pod's A2A endpoint
- Conversation-to-sandbox mapping is persisted via Kubernetes labels on `SandboxClaim` resources, enabling map reconstruction after scheduler restarts
- Scheduler-specific configuration (session idle TTL, shutdown policy, sandbox ready timeout) is managed via a watched `ConfigMap` with hot-reload
- Pod template and warm pool settings are managed via agent-sandbox's native `SandboxTemplate` and `SandboxWarmPool` CRDs
- The Helm chart supports both standalone mode (current behavior, default) and scheduler mode via a `scheduler.enabled` flag
- OpenTelemetry trace context passes through the scheduler with additional spans for sandbox lifecycle and proxy operations
- `k8s-agent-sandbox` Python package is added as a dependency for sandbox lifecycle management

## Capabilities

### New Capabilities
- `sandbox-session-management`: Lifecycle management of per-conversation sandbox pods — creation via SandboxClaim, readiness tracking, conversation-to-sandbox routing, idle TTL reaping, and label-based persistence across scheduler restarts
- `scheduler-a2a-proxy`: Transparent A2A HTTP reverse proxy that extracts conversation ID from A2A messages, routes to the correct sandbox endpoint, propagates headers (including OTEL trace context), and surfaces sandbox infrastructure errors as HTTP error responses
- `scheduler-configuration`: Hot-reloadable ConfigMap-based configuration for scheduler policy settings, plus Helm chart mode switching between standalone executor and scheduler+sandbox deployment
- `scheduler-observability`: OpenTelemetry instrumentation of the scheduler — trace context propagation from controller through scheduler to sandbox, with spans covering sandbox creation, name resolution, readiness waiting, and request proxying

### Modified Capabilities
_(none — the existing Claude Agent SDK executor runs unchanged inside sandbox pods)_

## Impact

- **New code**: `src/claude_agent_scheduler/` package within the existing `executors/claude-agent-sdk/` directory
- **Helm chart**: New templates for scheduler deployment, service, ConfigMap, RBAC, SandboxTemplate, and SandboxWarmPool; conditional rendering based on `scheduler.enabled`
- **Dependencies**: `k8s-agent-sandbox[async]` and `kubernetes_asyncio` added to the project
- **RBAC**: Two distinct service accounts — scheduler SA (sandbox CRD management) and sandbox executor SA (Ark CRD read access, existing)
- **Infrastructure prerequisite**: Requires the agent-sandbox controller to be installed in the cluster
- **No changes**: to the executor code, ark-sdk, Ark core, or the A2A protocol
