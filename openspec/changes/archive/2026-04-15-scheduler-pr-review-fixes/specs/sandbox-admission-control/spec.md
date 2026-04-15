## sandbox-admission-control

Configurable limit on the number of concurrent active sandboxes to prevent unbounded resource creation.

### Requirements

- [ ] New config field `max_active_sandboxes` (int, default 0 = unlimited) in `SchedulerConfig`
- [ ] Exposed in Helm values as `scheduler.config.maxActiveSandboxes`
- [ ] Exposed in ConfigMap for hot-reload
- [ ] Before `create_sandbox`, LIST claims with managed-by label selector and check count
- [ ] If `max_active_sandboxes > 0` and count >= limit, raise `SandboxCapacityError`
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
    maxActiveSandboxes: 0  # 0 = unlimited
```

### Defense-in-Depth

Document in values.yaml that operators can also set a namespace-level `ResourceQuota` on pods as a hard cap independent of the scheduler's soft limit.
