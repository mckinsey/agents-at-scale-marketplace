## Why

The ark-sdk `ExecutorApp` now supports real-time broker streaming via `stream_chunk()` on `BaseExecutor` (Phase 2 of mckinsey/agents-at-scale-ark#1891). Marketplace executors need to adopt it to deliver token-by-token streaming to the dashboard and CLI.

## What Changes

- `openai-responses` executor calls `await self.stream_chunk(token)` as tokens arrive from the OpenAI Responses API streaming loop
- `claude-agent-sdk` executor calls `await self.stream_chunk(token)` as tokens arrive from the Anthropic streaming API
- `langchain` executor calls `await self.stream_chunk(token)` as tokens arrive from LangChain streaming callbacks
- All three executors continue to return the full accumulated response from `execute_agent()` unchanged

## Capabilities

### New Capabilities
- `executor-broker-streaming`: marketplace executors stream tokens to the ark-broker in real time during `execute_agent()` by calling `self.stream_chunk()`

### Modified Capabilities

## Impact

- `executors/openai-responses/` — streaming loop calls `self.stream_chunk(token)`
- `executors/claude-agent-sdk/` — streaming callback calls `self.stream_chunk(token)`
- `executors/langchain/` — streaming handler calls `self.stream_chunk(token)`
- Requires ark-sdk version with `stream_chunk()` on `BaseExecutor` (Phase 2)
