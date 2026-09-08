## sandbox-admission-control

Configurable limit on the number of concurrent active sandboxes to prevent unbounded resource creation.

### Requirements

- [ ] New config field `max_active_sandboxes` (int, default 25, 0 = unlimited) in `SchedulerConfig`
- [ ] Exposed in Helm values as `scheduler.config.maxActiveSandboxes`
- [ ] Exposed in ConfigMap for hot-reload
- [ ] Occupancy is the set of claim names currently held, not a counter, so every update is idempotent
- [ ] Before `create_sandbox`, check occupancy against the limit without a K8s round-trip
- [ ] If `max_active_sandboxes > 0` and the claim is not already held and occupancy >= limit, raise `SandboxCapacityError`
- [ ] A claim name is added to the set before its CREATE is issued, so concurrent requests cannot exceed the limit
- [ ] A provisioning failure deletes the claim this call created and frees its slot; a claim adopted on 409 is left alone
- [ ] Reconciliation adopts every claim a LIST returns and drops only those it disproves, never claims reserved after the LIST was issued or still being provisioned
- [ ] Reconciliation runs on cache warm and on every reaper cycle
- [ ] Recovering a sandbox reuses the same deterministic claim name, so it replaces rather than adds and is net-neutral on occupancy
- [ ] Proxy maps `SandboxCapacityError` to HTTP 503 with `Retry-After: 30` header
- [ ] `get_sandbox` (follow-up messages to existing sandboxes) is never subject to admission control

### Error Response Format

```json
{
  "jsonrpc": "2.0",
  "id": "<from request>",
  "error": {
    "code": -32000,
    "message": "Sandbox capacity reached (100/100 active). Retry later."
  }
}
```

### Helm Values

```yaml
scheduler:
  config:
    maxActiveSandboxes: 25  # 0 = unlimited
```

### Defense-in-Depth

Document in values.yaml that operators can also set a namespace-level `ResourceQuota` on pods as a hard cap independent of the scheduler's soft limit.
