## ADDED Requirements

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
The executor SHALL read the Anthropic model name from the `ANTHROPIC_MODEL` environment variable, defaulting to `claude-sonnet-4-20250514` if not set.

#### Scenario: Custom model configured
- **WHEN** `ANTHROPIC_MODEL` is set to `claude-opus-4-20250514`
- **THEN** all ClaudeSDKClient sessions SHALL use that model

#### Scenario: No model configured
- **WHEN** `ANTHROPIC_MODEL` is not set
- **THEN** the executor SHALL use `claude-sonnet-4-20250514` as the default

### Requirement: API key from environment
The executor SHALL read `ANTHROPIC_API_KEY` from the environment. The Helm chart SHALL load this from a K8s secret named `anthropic-api-key`.

#### Scenario: API key missing
- **WHEN** `ANTHROPIC_API_KEY` is not set at startup
- **THEN** the executor SHALL fail to start with a clear error message

### Requirement: BaseExecutor integration
The executor SHALL extend `BaseExecutor` from `ark-sdk` and be served via `ExecutorApp`, following the same pattern as the langchain executor. It SHALL expose a health endpoint at `/health` on port 8000.

#### Scenario: Health check
- **WHEN** a GET request is made to `/health`
- **THEN** the executor SHALL respond with HTTP 200

### Requirement: ExecutionEngine CRD registration
The Helm chart SHALL create an `ExecutionEngine` custom resource (apiVersion: `ark.mckinsey.com/v1prealpha1`) that references the executor's K8s Service, enabling ARK to discover and route to this executor.

#### Scenario: ExecutionEngine created on install
- **WHEN** the Helm chart is installed
- **THEN** an ExecutionEngine CRD SHALL be created with a `serviceRef` pointing to the executor's ClusterIP service on port 8000
