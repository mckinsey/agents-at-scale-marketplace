## MODIFIED Requirements

### Requirement: Route returning conversations to existing sandboxes
The scheduler SHALL resolve conversation-to-sandbox mappings by querying the `SandboxClaim` in the K8s API using the deterministic claim name derived from the conversation ID. A short-lived local cache (approximately 5 seconds) MAY be used to avoid redundant API calls. The cache SHALL NOT be authoritative — a cache miss SHALL always fall through to a K8s API GET.

#### Scenario: Follow-up message in existing conversation (cache hit)
- **WHEN** an A2A request arrives with `contextId` set to `conv-abc-123` and the local cache contains a fresh entry for that conversation
- **THEN** the scheduler SHALL route the request directly to the cached sandbox endpoint without querying the K8s API

#### Scenario: Follow-up message in existing conversation (cache miss)
- **WHEN** an A2A request arrives with `contextId` set to `conv-abc-123` and the local cache has no entry or a stale entry
- **THEN** the scheduler SHALL GET the `SandboxClaim` by its deterministic name, resolve the sandbox service FQDN, populate the cache, and route the request

#### Scenario: Existing sandbox is no longer reachable
- **WHEN** an A2A request arrives for a conversation whose sandbox pod is unreachable (crashed, deleted)
- **THEN** the scheduler SHALL evict the cache entry, attempt to create a new sandbox, and forward the request to the new sandbox

### Requirement: Create sandbox for new conversation
The scheduler SHALL create a `SandboxClaim` referencing the configured `SandboxTemplate` when an A2A request arrives with a `contextId` that has no existing `SandboxClaim`. The claim SHALL be labeled with `ark.mckinsey.com/conversation-id` and `ark.mckinsey.com/managed-by: claude-agent-sdk-scheduler`. When multiple scheduler replicas race to create a claim for the same conversation, the K8s API SHALL resolve the conflict — the replica that receives 409 Conflict SHALL retrieve the existing claim and proceed.

#### Scenario: First message in a new conversation
- **WHEN** an A2A request arrives with `contextId` set to `conv-abc-123` and no `SandboxClaim` exists for that conversation
- **THEN** the scheduler SHALL create a `SandboxClaim` in the configured namespace, wait for the sandbox to become Ready, resolve its service FQDN, and cache the mapping

#### Scenario: Concurrent first messages from multiple replicas
- **WHEN** two scheduler replicas simultaneously receive the first message for the same conversation and both attempt to create a `SandboxClaim`
- **THEN** one replica SHALL succeed with 201 Created and the other SHALL receive 409 Conflict, retrieve the existing claim, and proceed to wait for the same sandbox

#### Scenario: Warm pool sandbox allocation
- **WHEN** a `SandboxWarmPool` exists with available pre-warmed pods and a new conversation arrives
- **THEN** the scheduler SHALL create a `SandboxClaim` and the agent-sandbox controller SHALL allocate a warm sandbox, resulting in faster readiness compared to cold creation

#### Scenario: Sandbox creation failure
- **WHEN** the `SandboxClaim` creation fails (K8s API error, quota exceeded)
- **THEN** the scheduler SHALL return HTTP 502 to the Ark controller with a descriptive error body

#### Scenario: Sandbox readiness timeout
- **WHEN** a sandbox does not become Ready within the configured `sandboxReadyTimeout`
- **THEN** the scheduler SHALL delete the `SandboxClaim` and return HTTP 502 to the Ark controller

### Requirement: Idle session reaping
The scheduler SHALL run a background task that periodically lists `SandboxClaims` with the managed-by label, checks the `ark.mckinsey.com/last-activity` annotation against the configured `sessionIdleTTL`, and deletes expired claims. Each scheduler replica SHALL run its own reaper independently — DELETE operations are idempotent and safe to execute concurrently.

#### Scenario: Conversation exceeds idle TTL
- **WHEN** a `SandboxClaim` has a `last-activity` annotation older than `sessionIdleTTL`
- **THEN** the scheduler SHALL delete the `SandboxClaim` and evict the conversation from its local cache

#### Scenario: Activity resets idle timer
- **WHEN** a new A2A request arrives for a conversation with an existing sandbox
- **THEN** the scheduler SHALL PATCH the `SandboxClaim`'s `ark.mckinsey.com/last-activity` annotation with the current timestamp

#### Scenario: Multiple replicas reap concurrently
- **WHEN** two scheduler replicas simultaneously detect an expired session and both attempt to delete the `SandboxClaim`
- **THEN** one SHALL succeed and the other SHALL receive 404 Not Found, which SHALL be treated as success

### Requirement: Rebuild conversation map on startup
The scheduler SHALL populate its local cache from Kubernetes on startup by listing all `SandboxClaim` resources with the managed-by label. This is a cache warming optimization — the scheduler SHALL also be able to serve requests via K8s API lookups if the cache is empty.

#### Scenario: Scheduler pod restarts
- **WHEN** the scheduler pod restarts
- **THEN** the scheduler SHALL list all managed `SandboxClaims`, resolve each to a sandbox endpoint, and populate the local cache before accepting requests

#### Scenario: Orphaned claims from previous scheduler instance
- **WHEN** the scheduler finds claims whose sandboxes are no longer Ready or no longer exist
- **THEN** the scheduler SHALL delete those orphaned claims during startup

### Requirement: Sandbox shutdown policy
When deleting a sandbox (idle reaping or explicit cleanup), the scheduler SHALL respect the configured `shutdownPolicy`. A policy of `Delete` SHALL remove the sandbox and its resources. A policy of `Retain` SHALL leave the sandbox for manual inspection.

#### Scenario: Delete shutdown policy
- **WHEN** a sandbox is reaped with `shutdownPolicy: Delete`
- **THEN** the scheduler SHALL delete the `SandboxClaim`, causing the agent-sandbox controller to delete the underlying Sandbox and Pod

#### Scenario: Retain shutdown policy
- **WHEN** a sandbox is reaped with `shutdownPolicy: Retain`
- **THEN** the scheduler SHALL evict the conversation from its local cache but SHALL NOT delete the `SandboxClaim`, leaving the sandbox running for inspection
