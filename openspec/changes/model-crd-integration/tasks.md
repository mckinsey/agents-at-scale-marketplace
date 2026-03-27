## 1. Core Executor Changes

- [ ] 1.1 Add `_resolve_model_config(request)` static method to `ClaudeAgentExecutor` that extracts `(model_name, api_key, base_url)` from `request.agent.model`, validates `anthropic` config is present with `apiKey`, and raises a clear error if missing
- [ ] 1.2 Update `execute_agent()` to call `_resolve_model_config()` and build an `env` dict with `ANTHROPIC_API_KEY` (and optionally `ANTHROPIC_BASE_URL`), passing it to `ClaudeAgentOptions(env=...)`
- [ ] 1.3 Remove `self.model` instance variable and `ANTHROPIC_MODEL` / `DEFAULT_MODEL` references from `__init__` — model name now comes per-request from the Model CRD

## 2. Helm Chart Changes

- [ ] 2.1 Remove the `anthropic-api-key` `secretRef` from `deployment.yaml` `envFrom`
- [ ] 2.2 Remove the `ANTHROPIC_MODEL` entry from `values.yaml` `app.env` list
- [ ] 2.3 Remove the `ANTHROPIC_MODEL` env var from `deployment.yaml` (rendered from values)

## 3. Tests

- [ ] 3.1 Add test for `_resolve_model_config()` with valid anthropic config — verifies correct extraction of model name, API key, and base URL
- [ ] 3.2 Add test for `_resolve_model_config()` with missing anthropic config — verifies clear error
- [ ] 3.3 Add test for `_resolve_model_config()` with missing apiKey — verifies clear error
- [ ] 3.4 Add test for `_resolve_model_config()` with no baseUrl — verifies base_url is None
- [ ] 3.5 Update existing MCP tests to provide model config on the request fixture

## 4. Documentation

- [ ] 4.1 Update CHANGELOG.md with breaking change note and migration instructions (create Model CRD, update Agent CRD reference, remove standalone secret)
