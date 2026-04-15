## Context

The Claude Agent SDK executor is deployed as a single long-lived pod that processes all A2A requests from the Ark controller. Sessions are isolated only at the filesystem level (`/data/sessions/<conversationId>/`). The executor extends `BaseExecutor` from `ark-sdk`, is served via `ExecutorApp` (which bridges A2A to the executor's `execute_agent()` method), and resolves Agent, Model, Tool, and MCPServer CRDs internally using its pod's service account.

The [kubernetes-sigs/agent-sandbox](https://github.com/kubernetes-sigs/agent-sandbox) project provides Kubernetes CRDs (`Sandbox`, `SandboxTemplate`, `SandboxClaim`, `SandboxWarmPool`) for managing ephemeral, isolated, stateful workloads — each with its own pod, service, and stable DNS identity.

The scheduler introduces a proxy layer between the Ark controller and the executor, delegating each conversation to its own sandbox pod running the unchanged executor image.

## Goals / Non-Goals

**Goals:**
- Full container-level isolation between concurrent agent sessions
- Zero changes to the existing Claude Agent SDK executor code
- Per-conversation sandbox lifecycle with idle TTL cleanup
- Warm pool support for fast sandbox allocation
- Hot-reloadable scheduler configuration
- Helm chart toggle between standalone executor and scheduler mode
- OTEL trace continuity through the scheduler

**Non-Goals:**
- Per-agent scheduler configuration (option A: single ConfigMap, one-size-fits-all)
- Custom CRDs for scheduler configuration
- Streaming/SSE support in the A2A proxy (current executor uses blocking A2A)
- Sandbox state snapshotting or hibernation
- Multi-cluster sandbox scheduling

## Decisions

### 1. A2A relay with unchanged executor in sandboxes

**Decision**: The scheduler is a transparent A2A HTTP reverse proxy. Sandbox pods run the identical executor image with the full `ExecutorApp` A2A stack. The scheduler forwards A2A HTTP requests as-is to the sandbox's A2A endpoint.

**Alternatives considered**:
- *Custom HTTP protocol*: Scheduler resolves CRDs and sends a simplified `ExecutionEngineRequest` directly to sandboxes via a custom endpoint. Would require modifying the executor to accept requests outside the A2A flow, violating the zero-change goal.
- *gRPC/exec-based communication*: Lower-level communication via pod exec. Would bypass the well-tested A2A path and add complexity.

**Rationale**: The A2A relay approach means the sandbox is functionally identical to a standalone executor deployment. This eliminates protocol translation bugs and keeps the blast radius of the scheduler change to new code only.

### 2. Conversation ID extracted from A2A `context_id`

**Decision**: The scheduler parses the incoming A2A JSON only enough to extract the top-level `context_id` field for routing. All other A2A content passes through opaquely.

**Rationale**: Ark core sets `context_id` from `Query.spec.conversationId` via `protocol.NewMessageWithContext()`. This is the canonical conversation identifier in the A2A flow. No need to parse QueryRef metadata or other extension fields.

### 3. CRD resolution stays in sandbox pods

**Decision**: Each sandbox pod resolves Agent, Model, Tool, MCPServer, and Secret CRDs using a shared service account, exactly as the standalone executor does today. The scheduler does not perform CRD resolution.

**Alternatives considered**:
- *Scheduler-side resolution*: Scheduler resolves all CRDs, passes fully-populated `ExecutionEngineRequest` to sandboxes. Would require a custom protocol (see Decision 1) and would centralize secret access in the scheduler.

**Rationale**: Keeps the unchanged-executor constraint. The shared service account provides the same trust model as the current single-pod deployment. Container isolation (optional gVisor/Kata runtime class) addresses the security concern of the Bash tool having CRD read access.

### 4. ConfigMap for scheduler policy, agent-sandbox CRDs for pod/pool config

**Decision**: Scheduler-specific settings (sessionIdleTTL, shutdownPolicy, sandboxReadyTimeout, template reference) live in a watched ConfigMap. Pod template and warm pool settings are managed via native `SandboxTemplate` and `SandboxWarmPool` CRDs.

**Alternatives considered**:
- *Custom CRD*: A `SchedulerConfig` CRD for all settings. Adds CRD maintenance burden with no benefit over ConfigMap for these simple key-value settings.
- *Everything in Helm values*: Requires chart upgrade to change any setting, no hot-reload.

**Rationale**: Uses the right abstraction for each concern. ConfigMap for scheduler behavior (lightweight, watchable). agent-sandbox CRDs for infrastructure concerns (the controller already knows how to reconcile them).

### 5. Kubernetes labels for conversation-to-sandbox persistence

**Decision**: Each `SandboxClaim` is labeled with `ark.mckinsey.com/conversation-id` and `ark.mckinsey.com/managed-by: claude-agent-sdk-scheduler`. On startup, the scheduler lists claims by label selector and rebuilds its in-memory routing table.

**Rationale**: Labels are the idiomatic Kubernetes mechanism for querying resources by metadata. No external state store needed. The label selector query is efficient and atomic.

### 6. HTTP 502 for sandbox infrastructure errors

**Decision**: When sandbox creation fails, times out, or becomes unreachable, the scheduler returns HTTP 502 with a descriptive error body. Executor-level A2A errors pass through with their original status codes.

**Rationale**: HTTP 502 (Bad Gateway) accurately describes the failure: the proxy could not reach the backend. The Ark controller already handles transport-level errors from external execution engines. A2A-formatted error responses would require the scheduler to understand A2A semantics beyond routing.

### 7. Two distinct RBAC scopes

**Decision**: The scheduler and sandbox pods use separate service accounts with minimal permissions:

- `scheduler-sa`: create/delete/list/watch `SandboxClaims`, get/list/watch `Sandboxes`, get/watch `ConfigMaps`
- `sandbox-executor-sa`: get `Queries`, `Agents`, `Models`, `Tools`, `MCPServers`, `Secrets`, `ConfigMaps` (same as current executor SA)

**Rationale**: Principle of least privilege. The scheduler never needs to read Ark CRDs or secrets. Sandbox pods never need to manage sandbox lifecycle resources.

### 8. Scheduler OTEL spans

**Decision**: The scheduler extracts incoming W3C trace context, creates child spans for sandbox lifecycle operations (`scheduler.route`, `scheduler.sandbox.create`, `scheduler.sandbox.wait_ready`, `scheduler.proxy.forward`), and injects trace context into proxied request headers.

**Rationale**: Without scheduler spans, there would be a gap in traces between the controller's dispatch span and the executor's execution span. Scheduler spans provide visibility into sandbox allocation latency, which is the primary new latency source.

## Risks / Trade-offs

**[Cold start latency for new conversations]** → Mitigated by `SandboxWarmPool` with pre-warmed pods. Without warm pool, first message in a conversation incurs full pod startup time (30-60s). With warm pool, reduced to claim resolution + readiness check (~1-3s).

**[Scheduler is a single point of failure]** → The scheduler pod itself is stateless (routing table rebuilds from labels). Standard Kubernetes `Deployment` with multiple replicas and leader election or shared-nothing routing (any replica can handle any request by querying labels) provides availability.

**[Resource overhead of per-conversation pods]** → Each sandbox runs a full executor process. For many concurrent light conversations, this uses more resources than the shared-pod model. Mitigated by idle TTL reaping and configurable resource requests in the `SandboxTemplate`.

**[agent-sandbox project maturity]** → The project is at `v1alpha1` from `kubernetes-sigs`. API may change. → Pin to a specific version. The surface we use (Sandbox, SandboxClaim, SandboxTemplate, SandboxWarmPool) is the core API unlikely to be removed.

**[Scheduler restart during active requests]** → In-flight proxied requests will fail. The controller's A2A call times out and the Query enters error state. → This is the same failure mode as the current executor pod restarting. No regression.

## Migration Plan

1. **Install agent-sandbox controller** in the cluster (prerequisite)
2. **Upgrade Helm chart** with `scheduler.enabled: false` (default) — no behavior change
3. **Enable scheduler mode** by setting `scheduler.enabled: true` in values — the ExecutionEngine CRD switches its serviceRef from the executor to the scheduler
4. **Rollback**: Set `scheduler.enabled: false` to revert to standalone executor mode. Existing sandboxes are cleaned up by TTL or manual deletion.

## Open Questions

- **Scheduler replicas**: Should the scheduler support multiple replicas with shared-nothing routing (each replica queries K8s labels on cache miss), or single-replica with leader election? Shared-nothing is simpler but may increase K8s API load.
- **Conversation end signal**: Is there an explicit signal from the Ark controller when a conversation ends, or does the scheduler rely solely on idle TTL for cleanup?
- **Warm pool sizing guidance**: What's a reasonable default for warm pool replicas? Depends on expected conversation concurrency.
