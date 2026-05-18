## Why

Ark core introduces a new Query `provisioning` phase and a `QueryStatusUpdater` SDK utility in ark-sdk. The Claude Agent SDK scheduler is the first consumer — it provisions sandbox pods on demand and needs to signal this state to users waiting on query results. Without this integration, the new phase goes unused and users still see "running" during the 10-60 second provisioning window.

## What Changes

- Integrate `QueryStatusUpdater` into the scheduler proxy: signal `provisioning` before sandbox creation and `running` after sandbox becomes ready.
- Add `patch` verb on `queries/status` subresource to the scheduler's RBAC role in the Helm chart.
- Unit tests for provisioning status updates during the sandbox lifecycle.

## Capabilities

### New Capabilities

_(none)_

### Modified Capabilities

- `scheduler-a2a-proxy`: Proxy calls `QueryStatusUpdater` to set Query phase to `provisioning` before sandbox creation and back to `running` after sandbox is ready.
- `sandbox-session-management`: Sandbox creation lifecycle includes Query status signaling at provisioning start and end.

## Impact

- **Scheduler proxy** (`executors/claude-agent-sdk/src/claude_agent_scheduler/proxy.py`): Calls status updater before/after sandbox provisioning in the request handler.
- **Sandbox manager** (`executors/claude-agent-sdk/src/claude_agent_scheduler/sandbox_manager.py`): Status updater passed through or called around `create_sandbox`.
- **Helm chart** (`executors/claude-agent-sdk/chart/`): Scheduler RBAC role gains `patch` on `queries/status` subresource.
- **Tests**: Unit tests for status update calls during sandbox lifecycle.
- **Cross-repo dependency**: Requires ark core `query-provisioning-status` change for the `provisioning` phase enum value and `QueryStatusUpdater` class in ark-sdk.
