## Context

PR #195 adds a scheduler for sandbox-based session isolation. A code review identified issues ranging from invalid K8s resource names to resource leaks and missing admission control. This change addresses all critical and high-priority findings plus select medium/low items.

The most impactful design decision is enforcing UUID4 as the session identity format at the scheduler boundary, which eliminates an entire class of naming/sanitization bugs rather than patching them individually.

## Goals / Non-Goals

**Goals:**
- All conversation IDs flowing through the scheduler are valid UUID4s
- httpx client is properly lifecycle-managed and scaled for per-sandbox routing
- Sandbox creation is bounded by a configurable limit
- Timeout behavior matches the config name (`sandbox_ready_timeout` = single timeout, not doubled)
- Reaper tests exercise the actual reaper code
- Clear error semantics: 400 for bad input, 404 for expired sessions, 503 for capacity

**Non-Goals:**
- Upstream validation of conversationId in Ark core or the CRD
- Streaming/SSE proxy support
- Watch-based reaper replacing periodic LIST
- Leader election for the reaper

## Decisions

### 1. UUID4-only session identity at the scheduler boundary

**Decision**: `extract_context_id` enforces that conversation IDs are UUID4. Missing IDs get a generated UUID4. Non-UUID4 IDs are rejected with 400.

**Alternatives considered**:
- *Sanitize in `_claim_name`*: Patch the symptom (invalid K8s names) but not the cause. Requires sanitization in claim name, label value, and directory path. Different malformed inputs could collide to the same sanitized name.
- *Coerce via UUID5*: Deterministic hash of arbitrary input into a UUID. Works but silently transforms the user's input — confusing when the returned contextId doesn't match what they sent.
- *Sanitize + warn*: Defense-in-depth but adds sanitization logic in multiple places for a case that shouldn't happen in the designed flow.

**Rationale**: The scheduler generates conversation IDs for new sessions (UUID4). Follow-up messages reuse the returned UUID. The only way a non-UUID arrives is if a user manually sets `spec.conversationId` to an arbitrary string — this is outside the designed flow. Rejecting it is the clearest contract: "the scheduler owns session identity."

This eliminates: invalid K8s names (#1), invalid label values (#2), and the need for any sanitization logic. UUIDs are always valid K8s names (36 chars, `[a-f0-9-]`), valid label values, and valid directory names.

### 2. Split ensure_sandbox into get/create

**Decision**: Replace `ensure_sandbox(cid) -> (info, is_new)` with two explicit methods:
- `get_sandbox(cid) -> SandboxInfo | None` — cache lookup, then K8s GET, never creates
- `create_sandbox(cid) -> SandboxInfo` — creates claim, waits for ready

The proxy decides which to call based on whether `extract_context_id` generated the UUID (new session) or received it (follow-up).

**Alternatives considered**:
- *Keep `ensure_sandbox` with an `allow_create` flag*: Works but the flag is a code smell — callers need to know when creation is appropriate.

**Rationale**: Explicit methods make the intent clear and enable admission control on `create_sandbox` only. `get_sandbox` returning None for an unknown UUID naturally maps to 404 — the session was either never created or was reaped.

### 3. Admission control via count-before-create

**Decision**: Before creating a sandbox, LIST claims with the managed-by label selector and check count against `max_active_sandboxes`. If at capacity, raise `SandboxCapacityError`. The proxy maps this to 503 with `Retry-After`.

**Alternatives considered**:
- *Cache count from reaper*: Stale by up to 30s, could overshoot the limit.
- *Atomic create-then-check-then-rollback*: Complex, adds a create+delete cycle when over limit.

**Rationale**: New conversation creation is a relatively infrequent event (not every request). One LIST per new conversation is acceptable K8s API load. The 409 conflict handling already prevents double-counting across replicas. Namespace-level `ResourceQuota` serves as defense-in-depth but can't distinguish scheduler sandboxes from other pods.

### 4. httpx client owned by the composition root

**Decision**: Create `httpx.AsyncClient` in `__main__.py` with explicit pool limits. Pass it to `create_proxy_app`. Close it in the lifespan context manager alongside `sandbox_manager` and `config_watcher`.

**Rationale**: Starlette skips `on_event("shutdown")` handlers when a custom `lifespan` is provided. The current handler in `proxy.py` never fires. Moving ownership to the composition root (`__main__.py`) and the lifespan ensures cleanup happens.

Pool limits: `max_connections=500, max_keepalive_connections=100`. Default httpx limits (100 total, 20 per host) are too low — each sandbox is a unique host, and agent execution holds connections for up to 600s.

### 5. Single deadline in _create_sandbox

**Decision**: Compute `deadline = time.monotonic() + timeout` once at the top of `_create_sandbox`. Pass `remaining = deadline - time.monotonic()` to each sub-call.

**Rationale**: Current code passes the full `sandbox_ready_timeout` to both `resolve_sandbox_name` and `wait_for_sandbox_ready`, each of which creates its own deadline. Worst case is 2x the configured timeout. The config name implies a single overall timeout.

### 6. Extract _reap_once for testability

**Decision**: Extract the single-cycle reaper logic from `run_reaper` into `_reap_once`. Fix evict-before-delete ordering inside `_reap_once`. Tests call `_reap_once` directly.

**Rationale**: Current tests reimplement the reaper algorithm inline and have 6 known divergences from the actual code (shutdown_policy check, cache eviction, label selector validation, creationTimestamp fallback, ValueError handling, dynamic claim_name extraction). Testing `_reap_once` directly eliminates all of these.

### 7. Recovery: health check before delete

**Decision**: In `recover_sandbox`, check if the sandbox claim still exists and sandbox is Ready before deleting. Only delete+recreate if the sandbox is genuinely gone.

**Rationale**: `ConnectError` is a strong signal but not conclusive — kube-proxy propagation delays can cause brief unreachability. A quick GET on the claim and sandbox status distinguishes "gone" from "temporarily unreachable" without the cost of deleting a live sandbox and losing in-flight state.

## Risks / Trade-offs

**[Strict UUID4 rejects valid use cases]** → Users who set `spec.conversationId` to a custom string get a 400 from the scheduler. The Ark CRD allows it, but the scheduler doesn't. Mitigation: clear error message explaining the constraint. The designed flow (omit conversationId, use the returned one) always works.

**[COUNT-before-create race]** → Two replicas could both count N-1 claims and both create, reaching N+1. Mitigation: this is a soft limit, not a hard guarantee. The 409 conflict handling means at most one extra sandbox. `ResourceQuota` provides a hard cap.

**[get_sandbox returns 404 for reaped sessions]** → A follow-up message arrives after the session TTL. The sandbox is gone. The user gets 404 instead of a new sandbox. This is correct behavior — the session state is lost, silently creating a new sandbox would be worse.
