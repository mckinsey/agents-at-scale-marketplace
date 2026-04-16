### Requirement: Execute user input via ClaudeSDKClient
The executor SHALL accept A2A requests containing `userInput.content` and `conversationId`, create or resume a Claude Agent SDK session, and return the agent's response as a single Message.

#### Scenario: New conversation
- **WHEN** a request arrives with a `conversationId` that has no existing session directory
- **THEN** the executor SHALL create `/data/sessions/<conversationId>/`, initialize a new `ClaudeSDKClient` with `cwd` set to that directory, send the user input via `client.query()`, collect the response from `client.receive_response()`, and return it as a Message with role `assistant`

#### Scenario: Resumed conversation
- **WHEN** a request arrives with a `conversationId` that has an existing session directory with prior SDK state
- **THEN** the executor SHALL initialize `ClaudeSDKClient` with `resume` targeting the existing session and `cwd` set to the session directory, send the new user input, and return the response

#### Scenario: Empty user input
- **WHEN** a request arrives with empty `userInput.content`
- **THEN** the executor SHALL return an error message indicating that user input is required

### Requirement: Session filesystem isolation
Each conversation SHALL have its own isolated filesystem directory at `/data/sessions/<conversationId>/`. The Claude Agent SDK's built-in tools (Read, Write, Edit, Bash, Grep, Glob) SHALL operate within this directory scope.

#### Scenario: File created in one session is not visible in another
- **WHEN** an agent in session A creates a file via the Write tool
- **THEN** that file SHALL exist only under `/data/sessions/<sessionA-conversationId>/` and SHALL NOT be accessible from session B's directory

### Requirement: Session persistence across pod restarts
Session state SHALL be stored on a PersistentVolumeClaim mounted at `/data/sessions/`. The SDK's internal session data (stored under `.claude/` within the session directory) SHALL survive pod restarts.

#### Scenario: Pod restarts mid-conversation
- **WHEN** the executor pod restarts and a request arrives with an existing `conversationId`
- **THEN** the executor SHALL resume the session from the persisted SDK state on the PVC

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

### Requirement: BaseExecutor integration
The executor SHALL extend `BaseExecutor` from `ark-sdk` and be served via `ExecutorApp`, following the same pattern as the langchain executor. It SHALL expose a health endpoint at `/health` on port 8000.

#### Scenario: Health check
- **WHEN** a GET request is made to `/health`
- **THEN** the executor SHALL respond with HTTP 200

### Requirement: Agent prompt passed as system instructions
When `request.agent.prompt` is non-empty, the executor SHALL pass it to the Claude Agent SDK via `ClaudeAgentOptions.system_prompt` using the preset-with-append pattern, preserving the SDK's built-in system prompt.

#### Scenario: Agent with prompt configured
- **WHEN** a request arrives with `request.agent.prompt` set to `"You are a security auditor. Review code for vulnerabilities."`
- **THEN** the executor SHALL set `system_prompt={"type": "preset", "preset": "claude_code", "append": "You are a security auditor. Review code for vulnerabilities."}` on `ClaudeAgentOptions`

#### Scenario: Agent with no prompt configured
- **WHEN** a request arrives with `request.agent.prompt` as an empty string
- **THEN** the executor SHALL NOT set `system_prompt` on `ClaudeAgentOptions`, preserving the SDK's default behavior

#### Scenario: Agent with parameterized prompt
- **WHEN** an Agent CRD has `spec.prompt: "Analyze {language} code"` with parameter `language` resolved to `"Python"` by the ark-sdk
- **THEN** `request.agent.prompt` SHALL already contain `"Analyze Python code"` and the executor SHALL pass it as-is via the preset-with-append pattern

### Requirement: ExecutionEngine CRD registration
The Helm chart SHALL create an `ExecutionEngine` custom resource (apiVersion: `ark.mckinsey.com/v1prealpha1`) that references the executor's K8s Service, enabling ARK to discover and route to this executor.

#### Scenario: ExecutionEngine created on install
- **WHEN** the Helm chart is installed
- **THEN** an ExecutionEngine CRD SHALL be created with a `serviceRef` pointing to the executor's ClusterIP service on port 8000
