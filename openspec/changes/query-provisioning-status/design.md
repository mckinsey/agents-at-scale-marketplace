## Context

The Claude Agent SDK scheduler provisions sandbox pods on demand via `SandboxClaim` creation. Today, the scheduler's proxy handler calls `create_sandbox()` and blocks until the sandbox is ready (up to 60s). During this time, the Query status shows "running" — indistinguishable from actual agent execution.

Ark core is adding a `provisioning` phase to the Query CRD and a `QueryStatusUpdater` class to ark-sdk. The scheduler needs to call this updater at the right points in its sandbox lifecycle to surface provisioning state to users.

The `QueryStatusUpdater` is injected into the executor context by `A2AExecutorAdapter` in ark-sdk. However, the scheduler is not a standard executor — it's a reverse proxy that sits in front of sandbox executors. It intercepts A2A requests before they reach the executor, so it needs access to the status updater at the proxy level, not the executor level.

## Goals / Non-Goals

**Goals:**
- Signal provisioning state to users during sandbox creation
- Add RBAC for the scheduler to patch Query status
- Keep the integration minimal — the scheduler calls two methods at two points

**Non-Goals:**
- Granular provisioning progress (claim created, waiting for pod, waiting for ready) — one "provisioning" signal is sufficient
- Status updates during sandbox recovery (existing sandbox unreachable) — recovery is fast and rare
- Status updates from the sandbox executor itself — only the scheduler knows about provisioning

## Decisions

### 1. Status updater instantiated in the proxy, not the executor

**Decision**: The scheduler proxy creates its own `QueryStatusUpdater` instance using the query ref extracted from the A2A request. It does not rely on the executor-level injection from `A2AExecutorAdapter`.

**Alternatives considered**:
- *Pass through executor context*: The scheduler would need to partially parse the A2A request as an executor context to get the injected updater. This conflates the proxy role with the executor role.

**Rationale**: The scheduler already extracts the A2A message body for `context_id` routing. Extracting the query ref from the same message metadata is straightforward. A standalone `QueryStatusUpdater` with the query ref and K8s client is simpler than wiring through the executor injection path.

### 2. Status updates in the proxy handler, not sandbox_manager

**Decision**: The proxy handler (`proxy.py`) calls `update_query_phase` before calling `create_sandbox()` and after it returns. The sandbox manager remains unaware of Query status.

**Alternatives considered**:
- *Status updates inside sandbox_manager*: `create_sandbox` would accept a status updater and call it internally. This couples sandbox lifecycle management to Query status concerns.

**Rationale**: The proxy handler is the orchestration point — it knows both the query context (from the A2A message) and the sandbox lifecycle (from the manager). Keeping status updates here maintains separation of concerns.

### 3. Only signal on new sandbox creation, not cache hits

**Decision**: The proxy only calls `update_query_phase("provisioning", ...)` when `is_new=True` (first message, no existing sandbox). Follow-up messages that hit a cached/existing sandbox skip the provisioning signal.

**Rationale**: Follow-up messages route to an already-running sandbox in milliseconds. There's nothing to provision, so signaling "provisioning" would be misleading.

## Risks / Trade-offs

**[Query ref extraction duplication]** → The proxy will extract the query ref from the A2A message metadata, duplicating logic that exists in ark-sdk's `extract_query_ref`. Mitigation: import and reuse `extract_query_ref` from ark-sdk rather than reimplementing.

**[RBAC scope]** → The scheduler ServiceAccount gains `patch` on `queries/status` across its namespace. This is the same scope granted to any executor using the status updater. The status subresource is separate from spec, so no risk of modifying query inputs.

**[Deployment ordering]** → This change depends on ark-sdk containing `QueryStatusUpdater`. If the scheduler is deployed before ark-sdk is updated, the import will fail. Mitigation: bump ark-sdk dependency version in the scheduler's requirements to the version containing the updater.
