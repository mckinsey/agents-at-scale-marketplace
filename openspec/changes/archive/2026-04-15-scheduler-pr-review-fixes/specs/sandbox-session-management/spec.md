## sandbox-session-management (modifications)

Updates to the sandbox lifecycle management addressing timeout, recovery, and reaper correctness.

### ensure_sandbox split

- [ ] Remove `ensure_sandbox` method
- [ ] Add `get_sandbox(conversation_id) -> SandboxInfo | None`: check cache, then K8s GET by deterministic claim name. Return None if not found. Never creates.
- [ ] Add `create_sandbox(conversation_id) -> SandboxInfo`: create claim, resolve sandbox name, wait for ready. Handles 409 conflict (another replica created first).
- [ ] `recover_sandbox` checks sandbox health before deleting (GET claim + check sandbox Ready status). Only delete+recreate if sandbox is genuinely gone.

### Single deadline in create_sandbox

- [ ] Compute `deadline = time.monotonic() + sandbox_ready_timeout` once at entry
- [ ] Pass `remaining = int(deadline - time.monotonic())` to `resolve_sandbox_name`
- [ ] Check remaining > 0, then pass to `wait_for_sandbox_ready`
- [ ] If remaining <= 0 at any point, raise `TimeoutError`

### Reaper extraction

- [ ] Extract `_reap_once(self) -> None` from `run_reaper`
- [ ] `run_reaper` becomes: `while True: sleep(30); await _reap_once()`
- [ ] Inside `_reap_once`, evict cache **before** deleting claim (reverse current order)
- [ ] `_reap_once` checks `shutdown_policy == "Delete"` before deleting (already does, but tests must verify)
- [ ] `_reap_once` handles missing annotation by falling back to `creationTimestamp`
- [ ] `_reap_once` catches `ValueError` on `fromisoformat` and treats as expired
