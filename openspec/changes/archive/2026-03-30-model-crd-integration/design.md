## Context

The Claude Agent SDK executor currently manages its own Anthropic credentials independently:
- API key: loaded from a dedicated `anthropic-api-key` K8s secret via `envFrom`
- Model: set via `ANTHROPIC_MODEL` env var (default `claude-sonnet-4-20250514`)
- Neither value comes from the Model CRD

Every other executor (LangChain, completions) reads configuration from `request.agent.model`, which is resolved from the Agent CRD's model reference → Model CRD → secrets already resolved by the platform. With mckinsey/agents-at-scale-ark#1469 adding native `provider: anthropic` to the Model CRD, the Claude Agent SDK executor should follow the same pattern.

The resolved model config available at `request.agent.model` provides:
- `name`: model identifier (e.g., `claude-sonnet-4-20250514`)
- `type`: provider string (`"anthropic"`)
- `config`: dict with `{"anthropic": {"apiKey": "...", "baseUrl": "...", ...}}`

All secrets are resolved upstream before reaching the executor.

## Goals / Non-Goals

**Goals:**
- Read API key, model name, and base URL from the Model CRD via `request.agent.model`
- Pass API key to Claude Code CLI subprocess via `ClaudeAgentOptions(env=...)` (thread-safe, per-request)
- Remove the executor's standalone `anthropic-api-key` secret and `ANTHROPIC_MODEL` env var
- Align with the same config pattern used by the LangChain executor

**Non-Goals:**
- System prompt integration (Agent CRD prompt → `ClaudeAgentOptions.system_prompt`) — this needs separate design since it would override Claude Code's built-in system prompt
- Supporting non-Anthropic providers (openai, azure, bedrock) — the Claude Agent SDK only works with Anthropic
- Backward-compatible fallback to env vars — clean cutover, Model CRD required

## Decisions

### 1. Use `ClaudeAgentOptions(env=...)` for API key passing

The Claude Agent SDK has no `api_key` parameter. It reads `ANTHROPIC_API_KEY` from the subprocess environment. `ClaudeAgentOptions` exposes an `env: dict[str, str]` field that is passed to the CLI subprocess.

**Chosen**: Pass API key via `env={"ANTHROPIC_API_KEY": api_key}` on each request.

**Alternative considered**: Set `os.environ["ANTHROPIC_API_KEY"]` globally at startup. Rejected because it's process-global state — if we ever support concurrent requests or multiple API keys, this breaks. The `env` dict is scoped per `ClaudeSDKClient` instance.

### 2. No fallback to environment variables

**Chosen**: Require Model CRD config. If `request.agent.model.config` doesn't contain `"anthropic"` with an `apiKey`, raise a clear error.

**Alternative considered**: Fall back to env vars when Model CRD config is absent. Rejected because it creates two config paths to maintain and test, and diverges from how every other executor works. A clean error message guides operators to the right setup.

### 3. Extract model config in a dedicated method

**Chosen**: Add a `_resolve_model_config()` static method that extracts and validates the anthropic config from the request, returning a typed tuple of `(model, api_key, base_url)`. Keeps `execute_agent` focused on orchestration.

### 4. Pass `ANTHROPIC_BASE_URL` when provided

If the Model CRD config includes a `baseUrl`, pass it as `ANTHROPIC_BASE_URL` in the env dict. This supports proxies, private endpoints, or custom API gateways without code changes.

## Risks / Trade-offs

**Breaking change for existing deployments** → Document migration: create Model CRD with `provider: anthropic`, reference it from Agent CRD, remove standalone secret. Include a sample Model CRD manifest in the CHANGELOG.

**Model CRD config not present at request time** → The executor validates config at request time and returns a clear error: `"Agent model must have provider 'anthropic' with apiKey configured via Model CRD"`. Operators see exactly what's missing.

**Claude Agent SDK `env` behavior** → The `env` dict is additive (merged with process env, not replacing it). Verified from SDK source: subprocess inherits process env with `env` dict values overlaid. No risk of losing other env vars (like `HOME`, `PATH`, `NODE_PATH`).
