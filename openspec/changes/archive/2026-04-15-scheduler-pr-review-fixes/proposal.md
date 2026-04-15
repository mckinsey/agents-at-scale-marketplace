## Why

PR #195 received a thorough code review surfacing correctness, safety, and test quality issues in the scheduler. The critical items will cause production failures on non-UUID conversation IDs, leak resources on shutdown, and allow unbounded sandbox creation. The high-priority items affect timeout correctness, test reliability, and connection pool behavior at scale.

## What Changes

### Session identity enforcement

The scheduler becomes the sole authority on session identity. `extract_context_id` enforces that conversation IDs are always UUID4s:

- **No contextId in message** — generate UUID4, inject into body (existing behavior)
- **Valid UUID4** — pass through (existing behavior)
- **Anything else** — reject with 400 ("contextId must be a valid UUID4 or omitted")

This eliminates the entire class of K8s naming/label sanitization bugs because UUIDs are always valid K8s names, label values, and directory names. The `_claim_name` function works unchanged.

### Sandbox lifecycle split

Replace `ensure_sandbox` (which always creates if not found) with explicit `get_sandbox` / `create_sandbox` methods. The proxy uses `is_new` from `extract_context_id` to decide which path:

- First message (scheduler generated UUID) → `create_sandbox`
- Follow-up (user-provided UUID) → `get_sandbox`, return 404 if not found

This enables clean admission control — only `create_sandbox` needs gating.

### Admission control

Add `max_active_sandboxes` config field. Before creating a sandbox, count existing claims. If at capacity, return 503 with `Retry-After`. Defense-in-depth via namespace `ResourceQuota` documented in values.yaml.

### httpx client lifecycle and pool limits

Move `httpx.AsyncClient` creation into `__main__.py`, pass it to `create_proxy_app`, close it in the lifespan context manager. Set pool limits appropriate for per-sandbox routing (each sandbox is a unique host). Remove the dead `on_event("shutdown")` handler.

### Single deadline in `_create_sandbox`

Compute a single deadline from `sandbox_ready_timeout` at the top of `_create_sandbox`. Pass remaining time to `resolve_sandbox_name` and `wait_for_sandbox_ready`. Current code applies the full timeout to each independently, doubling the effective timeout.

### Reaper extraction and test rewrite

Extract single-cycle logic from `run_reaper` into `_reap_once`. Fix evict-before-delete ordering. Rewrite `test_reaper.py` to call `_reap_once` directly instead of reimplementing the algorithm inline.

### Cleanup

- Remove dead `shutdown_event` and signal handlers from `__main__.py`
- Document streaming (SSE) as a known limitation
- Add comment explaining sandbox secrets RBAC scope
- Reduce httpx connect timeout from 10s to 3s (dead sandboxes fail at TCP level immediately)

## Capabilities

### New Capabilities

- `session-identity-enforcement`: Scheduler validates and normalizes conversation IDs to UUID4 format
- `sandbox-admission-control`: Configurable limit on concurrent active sandboxes with 503 backpressure

### Modified Capabilities

- `sandbox-session-management`: Split `ensure_sandbox` into `get_sandbox` / `create_sandbox`. Fix timeout doubling. Extract `_reap_once` with correct evict-before-delete ordering.
- `scheduler-a2a-proxy`: Use explicit get/create sandbox paths based on message type. httpx client managed externally with appropriate pool limits.

## Impact

- **Code**: `proxy.py` (extract_context_id expanded, httpx client externalized), `sandbox_manager.py` (ensure_sandbox split, timeout fix, _reap_once extraction), `__main__.py` (httpx lifecycle, remove dead code), `config.py` (add max_active_sandboxes)
- **Tests**: `test_reaper.py` rewritten against `_reap_once`. New tests for UUID4 validation/rejection, 404 on unknown session, admission control 503.
- **Docs**: README and docs MDX updated with session identity contract and admission control config.
- **Helm**: `values.yaml` updated with `scheduler.config.maxActiveSandboxes`, comment on secrets RBAC.
- **No changes**: to CRD schemas, executor code, A2A protocol, or Ark core.

## Non-Goals

- Validating conversationId upstream in Ark core (the scheduler is the enforcement boundary)
- Watch-based reaper (LIST at 30s is fine for v1)
- Streaming/SSE proxy support (documented as known limitation)
- Scoping sandbox secrets RBAC with resourceNames (secret names are dynamic, container isolation is the mitigation)
