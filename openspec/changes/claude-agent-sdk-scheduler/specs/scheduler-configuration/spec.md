## ADDED Requirements

### Requirement: ConfigMap-based scheduler configuration
The scheduler SHALL read its configuration from a `ConfigMap` in its namespace. The ConfigMap SHALL contain a `config.yaml` key with the following settings: `sessionIdleTTL` (duration), `shutdownPolicy` (Delete or Retain), `sandboxReadyTimeout` (duration), `sandboxTemplate` (SandboxTemplate name), and `namespace` (target namespace for sandboxes).

#### Scenario: Scheduler starts with valid ConfigMap
- **WHEN** the scheduler pod starts and the ConfigMap `claude-agent-sdk-scheduler-config` exists with valid settings
- **THEN** the scheduler SHALL parse the ConfigMap and apply the settings

#### Scenario: ConfigMap missing at startup
- **WHEN** the scheduler pod starts and the ConfigMap does not exist
- **THEN** the scheduler SHALL use default values: `sessionIdleTTL: 30m`, `shutdownPolicy: Delete`, `sandboxReadyTimeout: 60s`, `sandboxTemplate: claude-agent-sdk`, `namespace: default`

### Requirement: Hot-reload configuration on ConfigMap changes
The scheduler SHALL watch the ConfigMap for changes and apply updated settings without requiring a pod restart. Changed settings SHALL take effect for subsequent operations (new sandbox creations, next reap cycle) without affecting in-flight requests.

#### Scenario: sessionIdleTTL changed while running
- **WHEN** the ConfigMap is updated to change `sessionIdleTTL` from `30m` to `1h`
- **THEN** the scheduler SHALL apply the new TTL to the next reap cycle without restarting

#### Scenario: sandboxTemplate changed while running
- **WHEN** the ConfigMap is updated to change `sandboxTemplate` from `claude-agent-sdk` to `claude-agent-sdk-large`
- **THEN** the scheduler SHALL use the new template for all subsequently created sandboxes, existing sandboxes SHALL continue running with their original template

### Requirement: Helm chart mode switching
The Helm chart SHALL support a `scheduler.enabled` flag in `values.yaml`. When `false` (default), the chart SHALL render the standalone executor deployment. When `true`, the chart SHALL render the scheduler deployment, its ConfigMap, RBAC, SandboxTemplate, and optionally SandboxWarmPool, and the `ExecutionEngine` CRD SHALL point to the scheduler service instead of the executor service.

#### Scenario: Default installation (scheduler disabled)
- **WHEN** the Helm chart is installed with default values
- **THEN** the chart SHALL render the executor Deployment, Service, and ExecutionEngine pointing to the executor — identical to the current behavior

#### Scenario: Scheduler-enabled installation
- **WHEN** the Helm chart is installed with `scheduler.enabled: true`
- **THEN** the chart SHALL render the scheduler Deployment, scheduler Service, ConfigMap, scheduler RBAC, sandbox executor RBAC, SandboxTemplate, ExecutionEngine pointing to the scheduler service, and SHALL NOT render the standalone executor Deployment

#### Scenario: Warm pool enabled
- **WHEN** the Helm chart is installed with `scheduler.enabled: true` and `scheduler.warmPool.enabled: true`
- **THEN** the chart SHALL additionally render a `SandboxWarmPool` resource referencing the `SandboxTemplate`

### Requirement: Scheduler RBAC
The scheduler service account SHALL have permissions to create, delete, list, and watch `SandboxClaim` resources, get, list, and watch `Sandbox` resources, and get and watch `ConfigMap` resources in its namespace.

#### Scenario: Scheduler creates a SandboxClaim
- **WHEN** the scheduler attempts to create a `SandboxClaim` using its service account
- **THEN** the operation SHALL succeed due to the RBAC role binding

#### Scenario: Scheduler cannot access Ark CRDs
- **WHEN** the scheduler service account attempts to read Ark CRDs (Agents, Models, etc.)
- **THEN** the operation SHALL be denied — only sandbox executor pods have Ark CRD access

### Requirement: Sandbox executor RBAC
The Helm chart SHALL create a service account for sandbox executor pods with read access to Ark CRDs (Queries, Agents, Models, Tools, MCPServers) and Secrets/ConfigMaps. This service account SHALL be referenced in the `SandboxTemplate` pod spec.

#### Scenario: Sandbox pod resolves Agent CRD
- **WHEN** the executor in a sandbox pod calls `resolve_query()` to read Agent, Model, and Tool CRDs
- **THEN** the operations SHALL succeed using the shared sandbox executor service account
