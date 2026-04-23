## 1. Scheduler Proxy Integration

- [ ] 1.1 Extract query ref from A2A message metadata in proxy handler using `extract_query_ref` from ark-sdk
- [ ] 1.2 Instantiate `QueryStatusUpdater` with query ref and K8s client in proxy handler
- [ ] 1.3 Call `update_query_phase("provisioning", "ExecutorProvisioning", <message>)` before `create_sandbox()` when `is_new=True`
- [ ] 1.4 Call `update_query_phase("running", "QueryRunning", "Query is running")` after sandbox becomes ready
- [ ] 1.5 Wrap status update calls in try/except — log errors, do not block request flow

## 2. RBAC

- [ ] 2.1 Add `patch` verb on `queries/status` subresource to scheduler RBAC role in Helm chart

## 3. Tests

- [ ] 3.1 Unit test: new conversation triggers provisioning and running status updates around `create_sandbox`
- [ ] 3.2 Unit test: existing conversation (cache hit) skips status updates
- [ ] 3.3 Unit test: status update failure does not block sandbox creation or proxying
- [ ] 3.4 Unit test: sandbox creation failure after provisioning signal returns correct error response
