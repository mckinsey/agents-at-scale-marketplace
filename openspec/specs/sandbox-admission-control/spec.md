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
- [ ] Occupancy must be seeded by a successful LIST before a limit can be enforced. While `max_active_sandboxes > 0` and nothing has been seeded, `create_sandbox` raises `SandboxCapacityError` rather than admitting against an occupancy it has not read. An unlimited scheduler has nothing to enforce and does not wait for seeding
- [ ] A slot is freed only when no claim remains: a provisioning failure deletes the claim this call created, but a claim adopted on 409 is never deleted and keeps its slot
- [ ] Requests sharing a claim name share its claim state, so the last one to finish reads whether a claim is in the cluster now rather than its own earlier snapshot of it
- [ ] Reconciliation adopts claims a LIST returns and drops only those it disproves. A LIST is stale in both directions, so it neither drops a claim reserved after it was issued nor re-adopts one released after it was issued
- [ ] Reconciliation runs on cache warm and on every reaper cycle, and the first reaper cycle runs immediately so a failed cache warm does not leave occupancy unseeded for a full interval
- [ ] Recovering a sandbox reuses the same deterministic claim name, so it replaces rather than adds and is net-neutral on occupancy. It drops the slot when it deletes the stale claim, making the recreate a real admission that frees the slot again if it fails without leaving a claim
- [ ] Proxy maps `SandboxCapacityError` to HTTP 503 with `Retry-After: 30` header, on both the create and recovery paths
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
