## Why

The Claude Agent SDK executor manages its Anthropic API key and model configuration independently via a dedicated K8s secret and environment variables, bypassing the platform's Model CRD entirely. Now that the ark platform has a native `provider: anthropic` on the Model CRD (merged in mckinsey/agents-at-scale-ark#1469), the executor should read its configuration from the same Model CRD that every other executor uses — centralizing credential management and making model selection per-Agent rather than cluster-wide.

## What Changes

- The executor reads API key, model name, and base URL from `request.agent.model.config["anthropic"]` (resolved Model CRD config) instead of environment variables
- The `ANTHROPIC_MODEL` env var and `anthropic-api-key` K8s secret are removed from the Helm chart — all config comes from the Model CRD
- API key is passed to the Claude Code CLI subprocess via `ClaudeAgentOptions(env={"ANTHROPIC_API_KEY": ...})`, keeping it thread-safe and scoped per request
- **BREAKING**: Deploying the executor now requires an Agent CRD that references a Model CRD with `provider: anthropic` config. The standalone `anthropic-api-key` secret is no longer used.

## Capabilities

### New Capabilities

_(none — this modifies existing capabilities)_

### Modified Capabilities

- `claude-agent-execution`: Model configuration and API key sourcing change from environment variables to Model CRD via `request.agent.model`

## Impact

- **Code**: `executor.py` — model/API key resolution logic changes
- **Helm chart**: `deployment.yaml` — remove `anthropic-api-key` secretRef and `ANTHROPIC_MODEL` env var; `values.yaml` — remove `ANTHROPIC_MODEL` default
- **Tests**: `test_mcp_options.py` — update to reflect new model config flow; add tests for Model CRD config extraction
- **Existing deployments**: Must create an Anthropic Model CRD and reference it from their Agent CRD before upgrading
