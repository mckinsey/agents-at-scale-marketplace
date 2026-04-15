## 1. Project Setup

- [x] 1.1 Create `src/claude_agent_scheduler/` package directory with `__init__.py` and `__main__.py` entry point
- [x] 1.2 Add `k8s-agent-sandbox[async]`, `kubernetes_asyncio`, `httpx`, `opentelemetry-api`, and `opentelemetry-sdk` to project dependencies in `pyproject.toml`
- [x] 1.3 Add a `scheduler` console script entry point in `pyproject.toml` (e.g., `executor-claude-agent-scheduler`)

## 2. Scheduler Configuration

- [x] 2.1 Implement `SchedulerConfig` pydantic model with fields: `sessionIdleTTL`, `shutdownPolicy`, `sandboxReadyTimeout`, `sandboxTemplate`, `namespace`, and defaults
- [x] 2.2 Implement `ConfigWatcher` that watches a named ConfigMap using `kubernetes_asyncio` watch API and updates `SchedulerConfig` on changes
- [x] 2.3 Add config parsing from `config.yaml` key in the ConfigMap with YAML deserialization and validation

## 3. Sandbox Session Management

- [x] 3.1 Implement `SandboxManager` class wrapping `AsyncK8sHelper` from `k8s-agent-sandbox` — create claims, resolve sandbox names, wait for readiness, delete claims
- [x] 3.2 Implement conversation-to-sandbox routing table (`dict[str, SandboxInfo]`) with `SandboxInfo` dataclass holding claim name, sandbox name, service FQDN endpoint, and last activity timestamp
- [x] 3.3 Implement `ensure_sandbox()` method: lookup existing mapping or create new sandbox (claim → resolve name → wait ready → get serviceFQDN → store mapping)
- [x] 3.4 Add `ark.mckinsey.com/conversation-id` and `ark.mckinsey.com/managed-by` labels to `SandboxClaim` creation
- [x] 3.5 Implement startup map rebuild: list `SandboxClaims` by managed-by label, resolve each to sandbox name and serviceFQDN, populate routing table, clean up orphaned claims
- [x] 3.6 Implement idle session reaper background task: periodic check of last activity timestamps against `sessionIdleTTL`, delete claims and remove mappings for expired sessions
- [x] 3.7 Implement stale sandbox recovery: when a routed sandbox is unreachable, remove mapping and create a new sandbox for the conversation

## 4. A2A Proxy

- [x] 4.1 Implement FastAPI application with A2A endpoint that receives POST requests from the Ark controller
- [x] 4.2 Implement `context_id` extraction from A2A JSON request body (minimal parsing, treat rest as opaque)
- [x] 4.3 Handle missing/empty `context_id` by generating a unique conversation ID
- [x] 4.4 Implement HTTP reverse proxy using `httpx.AsyncClient`: forward request body and headers (excluding Host) to `http://<serviceFQDN>:8000/`, relay response status, headers, and body
- [x] 4.5 Implement error handling: return HTTP 502 for sandbox creation failures, readiness timeouts, and connection errors; pass through A2A-level errors as-is
- [x] 4.6 Add `/health` endpoint returning HTTP 200
- [x] 4.7 Update last activity timestamp on each proxied request for idle TTL tracking

## 5. Observability

- [x] 5.1 Set up OTEL TracerProvider in the scheduler with W3C TraceContext propagator (extract from incoming headers, inject into proxied headers)
- [x] 5.2 Add `scheduler.route` span wrapping each request with attributes: `sandbox.conversation_id`, `sandbox.name`, `sandbox.is_new`
- [x] 5.3 Add `scheduler.sandbox.create`, `scheduler.sandbox.resolve_name`, `scheduler.sandbox.wait_ready` spans in the sandbox creation path
- [x] 5.4 Add `scheduler.proxy.forward` span wrapping the HTTP round-trip to the sandbox, with HTTP status code attribute
- [x] 5.5 Mark spans with error status and descriptions on failures (creation timeout, connection error, etc.)

## 6. Helm Chart Templates

- [x] 6.1 Add `scheduler.enabled` flag to `values.yaml` with default `false`, plus `scheduler.config.*`, `scheduler.sandboxTemplate.*`, `scheduler.warmPool.*` value blocks
- [x] 6.2 Create `scheduler-deployment.yaml` template (conditional on `scheduler.enabled`): scheduler pod with ConfigMap volume, service account reference, health check on `/health`
- [x] 6.3 Create `scheduler-service.yaml` template: ClusterIP service for the scheduler
- [x] 6.4 Create `scheduler-configmap.yaml` template: render `config.yaml` from `scheduler.config.*` values
- [x] 6.5 Create `scheduler-rbac.yaml` template: ServiceAccount, Role (sandboxclaims CRUD, sandboxes read, configmaps read), RoleBinding
- [x] 6.6 Create `sandbox-rbac.yaml` template: shared ServiceAccount for sandbox executor pods with Ark CRD and Secret read access
- [x] 6.7 Create `sandbox-template.yaml` template: `SandboxTemplate` CRD using the executor image, sandbox SA, port 8000, health probe, resource requests from values
- [x] 6.8 Create `sandbox-warmpool.yaml` template (conditional on `scheduler.warmPool.enabled`): `SandboxWarmPool` referencing the SandboxTemplate
- [x] 6.9 Update `executionengine.yaml` template: serviceRef conditionally points to scheduler service or executor service based on `scheduler.enabled`
- [x] 6.10 Add conditional rendering to existing `deployment.yaml` and `service.yaml`: skip when `scheduler.enabled` is true

## 7. Entry Point and Integration

- [x] 7.1 Implement `__main__.py` that initializes ConfigWatcher, SandboxManager, OTEL, and starts the FastAPI app with uvicorn
- [x] 7.2 Ensure startup sequence: load config → rebuild conversation map → start reaper → start HTTP server
- [x] 7.3 Add graceful shutdown: stop accepting requests, wait for in-flight proxied requests, stop reaper

## 8. Testing

- [x] 8.1 Unit tests for `SchedulerConfig` parsing and defaults
- [x] 8.2 Unit tests for `context_id` extraction from A2A JSON (present, missing, empty)
- [x] 8.3 Unit tests for HTTP proxy logic using `httpx` mock transport (success, connection error, sandbox error pass-through)
- [x] 8.4 Unit tests for idle reaper logic (expired sessions, activity reset)
- [x] 8.5 Unit tests for startup map rebuild (happy path, orphaned claims cleanup)
- [x] 8.6 Integration test: scheduler + mock sandbox pod end-to-end A2A round-trip
