## sandbox-admission-control

Configurable limit on the number of concurrent active sandboxes to prevent unbounded resource creation.

### Requirements

- [ ] New config field `max_active_sandboxes` (int, default 25, 0 = unlimited) in `SchedulerConfig`
- [ ] Exposed in Helm values as `scheduler.config.maxActiveSandboxes`
- [ ] Exposed in ConfigMap for hot-reload
- [ ] Before `create_sandbox`, check the active count against the limit without a K8s round-trip
- [ ] If `max_active_sandboxes > 0` and count >= limit, raise `SandboxCapacityError`
- [ ] Admission counts in-flight creations, so concurrent requests cannot exceed the limit
- [ ] The active count is reconciled against a claim LIST on cache warm and on every reaper cycle
- [ ] Recovering a sandbox for an existing conversation replaces it rather than adding one, so it bypasses the limit
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
