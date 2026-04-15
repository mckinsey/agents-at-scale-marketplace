## 1. openai-responses executor

- [ ] 1.1 Add `await self.stream_chunk(token)` in the OpenAI Responses API streaming loop
- [ ] 1.2 Unit test that `stream_chunk()` is called once per token during streaming execution
- [ ] 1.3 Unit test that full response is still returned from `execute_agent()` correctly

## 2. claude-agent-sdk executor

- [ ] 2.1 Add `await self.stream_chunk(token)` for each text delta in the Anthropic streaming callback
- [ ] 2.2 Unit test that `stream_chunk()` is called once per text delta
- [ ] 2.3 Unit test that full response is still returned from `execute_agent()` correctly

## 3. langchain executor

- [ ] 3.1 Add `await self.stream_chunk(token)` in the LangChain streaming callback handler
- [ ] 3.2 Unit test that `stream_chunk()` is called once per token via the callback
- [ ] 3.3 Unit test that full response is still returned from `execute_agent()` correctly

## 4. Release coordination

- [ ] 4.1 Pin ark-sdk version with `stream_chunk()` support in each executor's `pyproject.toml`
- [ ] 4.2 Verify end-to-end: submit query, confirm incremental chunks appear in broker SSE stream
