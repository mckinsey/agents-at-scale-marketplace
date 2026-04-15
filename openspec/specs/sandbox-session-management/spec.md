## ADDED Requirements

### Requirement: Create sandbox for new conversation
The scheduler SHALL create a `SandboxClaim` referencing the configured `SandboxTemplate` when an A2A request arrives with a `context_id` that has no existing sandbox mapping. The claim SHALL be labeled with `ark.mckinsey.com/conversation-id: <context_id>` and `ark.mckinsey.com/managed-by: claude-agent-sdk-scheduler`.

#### Scenario: First message in a new conversation
- **WHEN** an A2A request arrives with `context_id` set to `conv-abc-123` and no sandbox exists for that conversation
- **THEN** the scheduler SHALL create a `SandboxClaim` in the configured namespace referencing the configured `SandboxTemplate`, labeled with `ark.mckinsey.com/conversation-id: conv-abc-123`, wait for the sandbox to become Ready, resolve its service FQDN from the Sandbox status, and store the conversation-to-sandbox mapping

#### Scenario: Warm pool sandbox allocation
- **WHEN** a `SandboxWarmPool` exists with available pre-warmed pods and a new conversation arrives
- **THEN** the scheduler SHALL create a `SandboxClaim` and the agent-sandbox controller SHALL allocate a warm sandbox, resulting in faster readiness compared to cold creation

#### Scenario: Sandbox creation failure
- **WHEN** the `SandboxClaim` creation fails (K8s API error, quota exceeded)
- **THEN** the scheduler SHALL return HTTP 502 to the Ark controller with a descriptive error body

#### Scenario: Sandbox readiness timeout
- **WHEN** a sandbox does not become Ready within the configured `sandboxReadyTimeout`
- **THEN** the scheduler SHALL delete the `SandboxClaim`, remove any partial mapping, and return HTTP 502 to the Ark controller

### Requirement: Route returning conversations to existing sandboxes
The scheduler SHALL maintain an in-memory mapping of conversation IDs to sandbox endpoints. When an A2A request arrives with a `context_id` that has an existing sandbox, the scheduler SHALL route the request to that sandbox without creating a new one.

#### Scenario: Follow-up message in existing conversation
- **WHEN** an A2A request arrives with `context_id` set to `conv-abc-123` and a sandbox already exists for that conversation
- **THEN** the scheduler SHALL route the request directly to the existing sandbox's A2A endpoint without creating a new `SandboxClaim`

#### Scenario: Existing sandbox is no longer reachable
- **WHEN** an A2A request arrives for a mapped conversation but the sandbox pod is unreachable (crashed, deleted)
- **THEN** the scheduler SHALL check sandbox health (GET claim + check sandbox Ready status) before deleting. Only delete and recreate the sandbox if it is genuinely gone.

### Requirement: Idle session reaping
The scheduler SHALL run a background task that periodically checks for conversations whose last activity exceeds the configured `sessionIdleTTL` and deletes their `SandboxClaim` resources.

#### Scenario: Conversation exceeds idle TTL
- **WHEN** a conversation's last A2A interaction was more than `sessionIdleTTL` ago
- **THEN** the scheduler SHALL delete the corresponding `SandboxClaim` and remove the conversation from its in-memory mapping

#### Scenario: Activity resets idle timer
- **WHEN** a new A2A request arrives for a conversation that has an existing sandbox
- **THEN** the scheduler SHALL update the last activity timestamp for that conversation, resetting the idle TTL countdown

### Requirement: Rebuild conversation map on startup
The scheduler SHALL reconstruct its conversation-to-sandbox mapping from Kubernetes on startup by listing all `SandboxClaim` resources with the label `ark.mckinsey.com/managed-by: claude-agent-sdk-scheduler`.

#### Scenario: Scheduler pod restarts
- **WHEN** the scheduler pod restarts
- **THEN** the scheduler SHALL query for all `SandboxClaims` with the managed-by label, resolve each claim's sandbox name and service FQDN, and populate the in-memory routing table before accepting A2A requests

#### Scenario: Orphaned claims from previous scheduler instance
- **WHEN** the scheduler finds claims whose sandboxes are no longer Ready or no longer exist
- **THEN** the scheduler SHALL delete those orphaned claims during startup recovery

### Requirement: Sandbox shutdown policy
When deleting a sandbox (idle reaping or explicit cleanup), the scheduler SHALL respect the configured `shutdownPolicy`. A policy of `Delete` SHALL remove the sandbox and its resources. A policy of `Retain` SHALL leave the sandbox for manual inspection.

#### Scenario: Delete shutdown policy
- **WHEN** a sandbox is reaped with `shutdownPolicy: Delete`
- **THEN** the scheduler SHALL delete the `SandboxClaim`, causing the agent-sandbox controller to delete the underlying Sandbox and Pod

#### Scenario: Retain shutdown policy
- **WHEN** a sandbox is reaped with `shutdownPolicy: Retain`
- **THEN** the scheduler SHALL remove the conversation from its routing table but SHALL NOT delete the `SandboxClaim`, leaving the sandbox running for inspection

### Requirement: ensure_sandbox split into get and create

The monolithic `ensure_sandbox` method SHALL be replaced with two distinct operations to separate the read path from the write path.

- [ ] Remove `ensure_sandbox` method
- [ ] Add `get_sandbox(conversation_id) -> SandboxInfo | None`: check cache, then K8s GET by deterministic claim name. Return None if not found. Never creates.
- [ ] Add `create_sandbox(conversation_id) -> SandboxInfo`: create claim, resolve sandbox name, wait for ready. Handles 409 conflict (another replica created first).
- [ ] `recover_sandbox` checks sandbox health before deleting (GET claim + check sandbox Ready status). Only delete+recreate if sandbox is genuinely gone.

### Requirement: Single deadline in create_sandbox

Sandbox creation SHALL use a single monotonic deadline to prevent timeout drift across sequential async steps.

- [ ] Compute `deadline = time.monotonic() + sandbox_ready_timeout` once at entry
- [ ] Pass `remaining = int(deadline - time.monotonic())` to `resolve_sandbox_name`
- [ ] Check remaining > 0, then pass to `wait_for_sandbox_ready`
- [ ] If remaining <= 0 at any point, raise `TimeoutError`

### Requirement: Reaper extraction

The reaper loop SHALL be refactored into a testable single-pass function with corrected eviction ordering.

- [ ] Extract `_reap_once(self) -> None` from `run_reaper`
- [ ] `run_reaper` becomes: `while True: sleep(30); await _reap_once()`
- [ ] Inside `_reap_once`, evict cache **before** deleting claim (reverse current order)
- [ ] `_reap_once` checks `shutdown_policy == "Delete"` before deleting (already does, but tests must verify)
- [ ] `_reap_once` handles missing annotation by falling back to `creationTimestamp`
- [ ] `_reap_once` catches `ValueError` on `fromisoformat` and treats as expired
