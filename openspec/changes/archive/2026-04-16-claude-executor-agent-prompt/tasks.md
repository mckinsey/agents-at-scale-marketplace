## 1. Core Implementation

- [x] 1.1 In `executor.py`, read `request.agent.prompt` and when non-empty, add `system_prompt={"type": "preset", "preset": "claude_code", "append": prompt}` to `ClaudeAgentOptions`

## 2. Tests

- [x] 2.1 Add test: when `request.agent.prompt` is non-empty, `ClaudeAgentOptions` is constructed with the correct `system_prompt` preset-with-append config
- [x] 2.2 Add test: when `request.agent.prompt` is empty, `ClaudeAgentOptions` has no `system_prompt` set
- [x] 2.3 Fix existing integration tests in `test_mcp_options.py` to explicitly set `request.agent.prompt = ""` so MagicMock doesn't return a truthy mock object for the prompt field

## 3. Documentation

- [x] 3.1 Update `README.md` to document that the Agent CRD prompt is passed through as appended system instructions
