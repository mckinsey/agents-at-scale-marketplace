## scheduler-a2a-proxy (modifications)

Updates to the A2A proxy for httpx lifecycle, error handling, and routing logic.

### httpx client lifecycle

- [ ] Remove `httpx.AsyncClient` creation from `create_proxy_app`
- [ ] Accept `http_client: httpx.AsyncClient` as a parameter to `create_proxy_app`
- [ ] Remove `on_event("shutdown")` handler (dead code — Starlette skips it when custom lifespan is provided)
- [ ] `http_client` created in `__main__.py` with pool limits: `max_connections=500, max_keepalive_connections=100`
- [ ] `http_client` closed in the lifespan context manager after `sandbox_manager.close()`
- [ ] Connect timeout reduced from 10s to 3s (dead sandboxes fail at TCP level immediately)

### Proxy routing logic

- [ ] Use `is_new` from `extract_context_id` to decide routing:
  - `is_new=True` → `sandbox_manager.create_sandbox(context_id)` (admission control applies)
  - `is_new=False` → `sandbox_manager.get_sandbox(context_id)`
- [ ] Map `get_sandbox` returning None to 404 response: "Session not found or expired"
- [ ] Map `SandboxCapacityError` to 503 response with `Retry-After: 30`
- [ ] Map non-UUID4 contextId to 400 response (handled in `extract_context_id`)

### Error response mapping

| Condition | HTTP | JSON-RPC error code | Message |
|-----------|------|-------------------|---------|
| Non-UUID4 contextId | 400 | -32602 | Invalid contextId |
| Unknown/expired session | 404 | -32001 | Session not found or expired |
| Sandbox capacity reached | 503 | -32000 | Sandbox capacity reached |
| Sandbox creation failed | 502 | -32603 | Sandbox creation failed |
| Proxy connection error | 502 | -32603 | Sandbox recovery failed |
