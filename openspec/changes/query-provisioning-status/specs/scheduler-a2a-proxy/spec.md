## MODIFIED Requirements

### Requirement: Proxy routing logic

The proxy SHALL use the `is_new` flag from `extract_context_id` to select between create and get paths, with explicit error mapping for each failure mode. When `is_new=True`, the proxy SHALL signal Query provisioning status before and after sandbox creation.

- [ ] Use `is_new` from `extract_context_id` to decide routing:
  - `is_new=True` → call `update_query_phase("provisioning", "ExecutorProvisioning", <message>)`, then `sandbox_manager.create_sandbox(context_id)`, then `update_query_phase("running", "QueryRunning", "Query is running")` (admission control applies)
  - `is_new=False` → `sandbox_manager.get_sandbox(context_id)` (no status update)
- [ ] Map `get_sandbox` returning None to 404 response: "Session not found or expired"
- [ ] Map `SandboxCapacityError` to 503 response with `Retry-After: 30`
- [ ] Map non-UUID4 contextId to 400 response (handled in `extract_context_id`)
- [ ] Extract query ref from A2A message metadata using `extract_query_ref` from ark-sdk
- [ ] Instantiate `QueryStatusUpdater` with query ref and K8s client
- [ ] Status update failures SHALL be logged and ignored — they SHALL NOT block sandbox creation or request proxying

#### Scenario: New conversation triggers provisioning status
- **WHEN** an A2A request arrives with `is_new=True` and sandbox creation is required
- **THEN** the proxy SHALL set Query phase to `provisioning` with reason `ExecutorProvisioning` before calling `create_sandbox`, and set phase to `running` with reason `QueryRunning` after the sandbox becomes ready

#### Scenario: Existing conversation skips provisioning status
- **WHEN** an A2A request arrives with `is_new=False` and an existing sandbox is found
- **THEN** the proxy SHALL NOT call the status updater and SHALL route directly to the sandbox

#### Scenario: Status update fails during provisioning
- **WHEN** the `update_query_phase` call fails (K8s API error, missing query ref)
- **THEN** the proxy SHALL log the error and continue with sandbox creation and request proxying

#### Scenario: Sandbox creation fails after provisioning signal
- **WHEN** the proxy signals `provisioning` but sandbox creation subsequently fails
- **THEN** the proxy SHALL return the appropriate error response (502/503) — the Query phase will be overwritten by the controller's error handling
