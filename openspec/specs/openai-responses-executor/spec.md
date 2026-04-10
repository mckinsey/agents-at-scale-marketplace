## Requirements: OpenAI Responses API Executor

### Requirement: Execute agent via OpenAI Responses API
The executor SHALL accept A2A requests and call `POST /v1/responses` using the OpenAI Python SDK,
returning the assistant's text output as a single `Message`.

#### Scenario: First turn
- **WHEN** a request arrives with no prior conversation state
- **THEN** the executor SHALL call `client.responses.create()` with `model`, `instructions`, and
  `input` built from `request.history` + `request.userInput.content`

#### Scenario: Resumed conversation
- **WHEN** a request arrives and a `response_id` exists for the `conversationId`
- **THEN** the executor SHALL call `client.responses.create()` with `previous_response_id` set to
  the stored ID and `input` set to `request.userInput.content` (no history resend)

---

### Requirement: Model configuration from Model CRD
The executor SHALL read the OpenAI model ID from `request.agent.model.name` and the API key from
`request.agent.model.config["openai"]["apiKey"]`.

#### Scenario: Model name and key resolved
- **WHEN** a request arrives with a valid Model CRD referencing provider `openai`
- **THEN** the executor SHALL use `model.name` as the `model` parameter and `config["openai"]["apiKey"]`
  as the API key for the `AsyncOpenAI` client

#### Scenario: Optional base URL
- **WHEN** `request.agent.model.config["openai"]["baseUrl"]` is set
- **THEN** the executor SHALL pass it as `base_url` to `AsyncOpenAI`

#### Scenario: Missing OpenAI config
- **WHEN** `request.agent.model.config` has no `"openai"` key
- **THEN** the executor SHALL raise a `ValueError` describing the missing configuration

---

### Requirement: Built-in tool configuration via annotation cascade
Built-in tool configuration SHALL be read from the annotation key
`executor-openai-responses.ark.mckinsey.com/tools` on the ExecutionEngine, Agent, and Query CRs.
The value SHALL be a JSON array of tool objects following the OpenAI Responses API tool schema.

Cascade order (lowest → highest priority): **ExecutionEngine → Agent → Query**.
Merge semantics: each layer replaces entries with matching `type` keys and adds new ones.

#### Scenario: Agent enables web search with location
- **WHEN** an Agent CR has the annotation with value
  `[{"type": "web_search_preview", "user_location": {"type": "approximate", "country": "GB"}}]`
- **THEN** the executor SHALL include that object verbatim in the `tools` array sent to the Responses API

#### Scenario: Query overrides tool config
- **WHEN** both Agent and Query CRs set the annotation with the same `type`
- **THEN** the Query's entry SHALL replace the Agent's entry for that type

#### Scenario: Cascade adds new types
- **WHEN** the Agent annotation contains `web_search_preview` and the Query annotation contains `file_search`
- **THEN** both tool objects SHALL appear in the merged `tools` array

#### Scenario: Invalid annotation JSON
- **WHEN** the annotation value is malformed JSON
- **THEN** the executor SHALL log a warning and treat that layer as an empty list (do not raise)

#### Scenario: Annotation not a JSON array
- **WHEN** the annotation value is valid JSON but not an array
- **THEN** the executor SHALL log a warning and treat that layer as an empty list

---

### Requirement: Built-in tools run in OpenAI's runtime, not the executor's
Built-in tools (`web_search_preview`, `file_search`, `code_interpreter`, `computer_use_preview`)
are executed entirely within OpenAI's server-side runtime. The executor's only responsibility is to
declare them in the `tools` array. OpenAI never returns a `function_call` output item for them —
it returns a final `message` output directly, after running the tool internally.

This is the fundamental difference from the Completions API: in Completions, the model signals
a tool call and the client must execute it and reply. In the Responses API, built-in tools are
a closed loop on OpenAI's side; the executor is not in the loop.

#### Scenario: Web search runs without executor involvement
- **WHEN** `web_search_preview` is declared in `tools` and the model decides to search
- **THEN** OpenAI SHALL execute the search internally and return a `message` output item with the
  result; the executor SHALL NOT receive a `function_call` item for this tool

#### Scenario: No client-side execution for built-in tools
- **WHEN** the Responses API response contains no `function_call` output items
- **THEN** the executor SHALL NOT attempt any tool execution and SHALL return the text output directly

---

### Requirement: Custom function tools from request.tools
The executor SHALL convert each `ToolDefinition` in `request.tools` into an OpenAI `function` tool
and include them alongside built-in tools in every Responses API call.

#### Scenario: Function tool included
- **WHEN** `request.tools` contains a `ToolDefinition` with `name`, `description`, and `parameters`
- **THEN** the executor SHALL include `{"type": "function", "name": ..., "description": ..., "parameters": ...}`
  in the `tools` array

---

### Requirement: Function call tool loop
Unlike built-in tools, `function` type tools require client-side execution. When the Responses API
returns a `function_call` output item, the executor SHALL execute the function and send the result
back in a continuation call, up to `MAX_TOOL_ITERATIONS` times.

#### Scenario: Function call executed and result sent
- **WHEN** the Responses API returns a `function_call` item
- **THEN** the executor SHALL call `_execute_function_call`, wrap the result as
  `{"type": "function_call_output", "call_id": ..., "output": ...}`, and send it via
  `responses.create()` with `previous_response_id`

#### Scenario: Max iterations reached
- **WHEN** the tool loop runs for `MAX_TOOL_ITERATIONS` turns without a final text response
- **THEN** the executor SHALL return a Message indicating the iteration limit was reached

---

### Requirement: Session persistence
The executor SHALL persist the latest `response.id` per `conversationId` to a PVC-backed directory
at `SESSIONS_DIR/<conversationId>/response_id`, surviving pod restarts.

#### Scenario: Response ID saved
- **WHEN** a Responses API call completes
- **THEN** the executor SHALL write `response.id` to `SESSIONS_DIR/<conversationId>/response_id`

#### Scenario: Response ID read on resume
- **WHEN** a request arrives for an existing `conversationId`
- **THEN** the executor SHALL read the stored ID and use it as `previous_response_id`
