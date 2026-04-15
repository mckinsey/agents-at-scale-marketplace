## ADDED Requirements

### Requirement: openai-responses executor streams tokens to broker

The `openai-responses` executor SHALL call `await self.stream_chunk(token)` for each token received from the OpenAI Responses API streaming loop inside `execute_agent()`.

#### Scenario: openai-responses streams tokens during execution

- **WHEN** `execute_agent()` is called and the OpenAI Responses API returns a streaming response
- **THEN** each token is forwarded to the broker via `self.stream_chunk(token)` as it arrives
- **AND** the full accumulated response is still returned from `execute_agent()`

#### Scenario: openai-responses falls back when streaming unavailable

- **WHEN** `execute_agent()` is called and the model is configured for non-streaming
- **THEN** no `stream_chunk()` calls are made and the single-chunk fallback in `ExecutorApp` handles broker delivery

### Requirement: claude-agent-sdk executor streams tokens to broker

The `claude-agent-sdk` executor SHALL call `await self.stream_chunk(token)` for each text delta received from the Anthropic streaming API inside `execute_agent()`.

#### Scenario: claude-agent-sdk streams tokens during execution

- **WHEN** `execute_agent()` is called and the Anthropic API returns a streaming response
- **THEN** each text delta is forwarded to the broker via `self.stream_chunk(token)` as it arrives
- **AND** the full accumulated response is still returned from `execute_agent()`

### Requirement: langchain executor streams tokens to broker

The `langchain` executor SHALL call `await self.stream_chunk(token)` for each token received via the LangChain streaming callback inside `execute_agent()`.

#### Scenario: langchain streams tokens during execution

- **WHEN** `execute_agent()` is called with a LangChain chain configured for streaming
- **THEN** each token from the streaming callback is forwarded to the broker via `self.stream_chunk(token)`
- **AND** the full accumulated response is still returned from `execute_agent()`
