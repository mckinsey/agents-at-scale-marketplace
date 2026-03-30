## MODIFIED Requirements

### Requirement: Model configuration via environment variable
The executor SHALL read the Anthropic model name from `request.agent.model.name`, which is resolved from the Model CRD referenced by the Agent CRD. The executor SHALL NOT read model configuration from environment variables.

#### Scenario: Model name from Model CRD
- **WHEN** a request arrives with `request.agent.model.name` set to `claude-opus-4-20250514`
- **THEN** the executor SHALL use `claude-opus-4-20250514` as the model in `ClaudeAgentOptions`

#### Scenario: Missing model config
- **WHEN** a request arrives with `request.agent.model.config` that does not contain an `"anthropic"` key
- **THEN** the executor SHALL raise an error with message indicating that the Agent's Model CRD must have `provider: anthropic` with valid config

### Requirement: API key from environment
The executor SHALL read the Anthropic API key from `request.agent.model.config["anthropic"]["apiKey"]`, which is resolved from the Model CRD's `spec.config.anthropic.apiKey` field (secrets resolved upstream by the platform). The API key SHALL be passed to the Claude Code CLI subprocess via `ClaudeAgentOptions(env={"ANTHROPIC_API_KEY": ...})`.

#### Scenario: API key from Model CRD
- **WHEN** a request arrives with `request.agent.model.config["anthropic"]["apiKey"]` set to a valid key
- **THEN** the executor SHALL pass the key to the Claude Code subprocess via the `env` parameter on `ClaudeAgentOptions`

#### Scenario: API key missing from Model CRD config
- **WHEN** a request arrives with `request.agent.model.config["anthropic"]` present but `apiKey` is empty or missing
- **THEN** the executor SHALL raise an error indicating that the Model CRD's anthropic config must include an apiKey

#### Scenario: Base URL from Model CRD
- **WHEN** a request arrives with `request.agent.model.config["anthropic"]["baseUrl"]` set to `https://proxy.internal.example.com`
- **THEN** the executor SHALL pass `ANTHROPIC_BASE_URL=https://proxy.internal.example.com` in the `env` parameter on `ClaudeAgentOptions`

#### Scenario: No base URL configured
- **WHEN** a request arrives with no `baseUrl` in `request.agent.model.config["anthropic"]`
- **THEN** the executor SHALL NOT set `ANTHROPIC_BASE_URL`, allowing the Claude SDK to use its default endpoint

## REMOVED Requirements

### Requirement: Model configuration via environment variable
**Reason**: Replaced by Model CRD-based configuration. Model name now comes from `request.agent.model.name` resolved from the platform's Model CRD.
**Migration**: Create a Model CRD with `provider: anthropic` and `model.value: <model-name>`, reference it from the Agent CRD.

### Requirement: API key from environment
**Reason**: Replaced by Model CRD-based configuration. API key now comes from `request.agent.model.config["anthropic"]["apiKey"]`, resolved from the Model CRD's secret reference.
**Migration**: Move the API key into the Model CRD's `spec.config.anthropic.apiKey.valueFrom.secretKeyRef` and remove the standalone `anthropic-api-key` K8s secret.
