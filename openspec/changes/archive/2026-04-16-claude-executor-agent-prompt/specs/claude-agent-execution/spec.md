## ADDED Requirements

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
