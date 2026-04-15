## 1. Session Identity Enforcement

- [ ] 1.1 Update `extract_context_id` signature to return `(context_id, body, is_new)` tuple
- [ ] 1.2 Add UUID4 validation: `uuid.UUID(value, version=4)` check on incoming contextId
- [ ] 1.3 Return JSON-RPC error (code -32602) for non-UUID4 contextId values
- [ ] 1.4 Update proxy handler to use `is_new` flag for routing decisions
- [ ] 1.5 Update `test_context_id.py` with cases: missing contextId, valid UUID4, invalid string, UUID5 (rejected), empty string

## 2. Sandbox Lifecycle Split

- [ ] 2.1 Add `get_sandbox(conversation_id) -> SandboxInfo | None` method: cache check → K8s GET → return None if not found
- [ ] 2.2 Rename `_create_sandbox` to `create_sandbox` (public) with admission control check at entry
- [ ] 2.3 Remove `ensure_sandbox` method
- [ ] 2.4 Update proxy handler: `is_new=True` → `create_sandbox`, `is_new=False` → `get_sandbox`
- [ ] 2.5 Update proxy to return 404 JSON-RPC error when `get_sandbox` returns None
- [ ] 2.6 Update `recover_sandbox` to check claim existence and sandbox Ready status before delete+recreate
- [ ] 2.7 Update `test_sandbox_manager.py` (or equivalent) for get/create split, 409 conflict, recovery health check

## 3. Admission Control

- [ ] 3.1 Add `max_active_sandboxes: int = 0` field to `SchedulerConfig`
- [ ] 3.2 Add `maxActiveSandboxes` to `_normalize_keys` mapping in `config.py`
- [ ] 3.3 Add `SandboxCapacityError` exception class
- [ ] 3.4 In `create_sandbox`, LIST claims and check count before creating if `max_active_sandboxes > 0`
- [ ] 3.5 Update proxy to catch `SandboxCapacityError` and return 503 with `Retry-After: 30`
- [ ] 3.6 Add `scheduler.config.maxActiveSandboxes` to Helm `values.yaml` and ConfigMap template
- [ ] 3.7 Tests: at-capacity rejection, under-capacity creation, unlimited (0) bypasses check

## 4. httpx Client Lifecycle

- [ ] 4.1 Remove `httpx.AsyncClient` creation from `create_proxy_app` in `proxy.py`
- [ ] 4.2 Add `http_client` parameter to `create_proxy_app` function signature
- [ ] 4.3 Remove `on_event("shutdown")` handler from `proxy.py`
- [ ] 4.4 Create `httpx.AsyncClient` in `__main__.py` with `Limits(max_connections=500, max_keepalive_connections=100)` and `Timeout(600.0, connect=3.0)`
- [ ] 4.5 Close `http_client` in lifespan context manager (after yield, before `sandbox_manager.close()`)
- [ ] 4.6 Update integration tests that create the proxy app to pass a mock/real http_client

## 5. Timeout Fix

- [ ] 5.1 Compute `deadline = time.monotonic() + self._config.sandbox_ready_timeout` at top of `create_sandbox`
- [ ] 5.2 Pass `remaining = int(deadline - time.monotonic())` to `resolve_sandbox_name`
- [ ] 5.3 Check `remaining > 0` before calling `wait_for_sandbox_ready`, raise `TimeoutError` if expired
- [ ] 5.4 Pass remaining to `wait_for_sandbox_ready`
- [ ] 5.5 Test: verify total wall time does not exceed `sandbox_ready_timeout` when both sub-calls are slow

## 6. Reaper Extraction and Test Rewrite

- [ ] 6.1 Extract `_reap_once(self) -> None` from `run_reaper` containing the single-cycle logic
- [ ] 6.2 `run_reaper` becomes `while True: await asyncio.sleep(30); await self._reap_once()`
- [ ] 6.3 In `_reap_once`, evict cache **before** deleting claim
- [ ] 6.4 Rewrite `test_reaper.py` to call `manager._reap_once()` directly with mocked K8s
- [ ] 6.5 Test: expired claim with `shutdown_policy=Delete` → cache evicted then claim deleted
- [ ] 6.6 Test: expired claim with `shutdown_policy=Retain` → cache evicted, claim NOT deleted
- [ ] 6.7 Test: fresh claim → no eviction, no deletion
- [ ] 6.8 Test: missing annotation → falls back to `creationTimestamp`
- [ ] 6.9 Test: unparseable annotation → treated as expired
- [ ] 6.10 Test: verify label selector `LABEL_MANAGED_BY=...` is passed to list call

## 7. Cleanup

- [ ] 7.1 Remove `shutdown_event` and signal handler registrations from `__main__.py` (lines 35, 43, 58-59)
- [ ] 7.2 Add comment to `sandbox-rbac.yaml` explaining why `secrets` `get` is namespace-wide (dynamic secret names from Model CRD, container isolation is the mitigation)
- [ ] 7.3 Document streaming/SSE as known limitation in README and docs MDX (proxy buffers full response)

## 8. Documentation Updates

- [ ] 8.1 Update README "How it works" section: document session identity contract (UUID4 only, scheduler-generated)
- [ ] 8.2 Update docs MDX "Scheduler Mode" section: add session identity explanation
- [ ] 8.3 Add `maxActiveSandboxes` to scheduler configuration tables in both README and docs MDX
- [ ] 8.4 Add "Known Limitations" subsection to scheduler docs: streaming not supported, full response buffered
- [ ] 8.5 Update "Session Behavior" section: clarify that conversationId should be omitted for new sessions and reused from Query status for follow-ups
