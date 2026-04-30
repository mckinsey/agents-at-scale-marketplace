# Agent CRD Prompt Support for Claude Agent SDK Executor

## Problem

The Claude Agent SDK executor ignores the `prompt` field from the Agent CRD. When a user configures an agent with a prompt (persona, role instructions, behavioral rules), that context never reaches the Claude subprocess — every agent executes with the SDK's default minimal system prompt regardless of its CRD configuration.

The data is available: the ark-sdk query extension resolves the Agent CRD, templates parameters into the prompt, and delivers the result as `request.agent.prompt` in the `ExecutionEngineRequest`. The executor receives it but never uses it.

The built-in completions executor handles this correctly — it resolves the prompt and prepends it as a system message to the conversation. The Claude executor needs parity.

## Solution

Pass `request.agent.prompt` to the Claude Agent SDK via `ClaudeAgentOptions.system_prompt` using the preset-with-append pattern:

```python
system_prompt={"type": "preset", "preset": "claude_code", "append": request.agent.prompt}
```

This preserves the SDK's built-in system prompt (tool instructions, safety guidelines) and appends the agent's custom prompt as additional instructions.

### Behavior

- **Prompt set on Agent CRD**: Built-in system prompt is preserved; agent prompt is appended via `system_prompt={"type": "preset", "preset": "claude_code", "append": prompt}`.
- **No prompt on Agent CRD**: No `system_prompt` parameter is set — current default behavior, unchanged.
- **Parameter templating**: Already handled upstream by the ark-sdk query extension (`_build_agent_config` resolves `{param}` placeholders before the executor sees the prompt).

### Mapping

```
Agent CRD                    ark-sdk                         ClaudeAgentOptions
──────────                   ───────                         ──────────────────
spec.prompt: "You are..."  → request.agent.prompt: "You.."  → system_prompt.append: "You are..."
spec.description: "..."    → request.agent.description       → (not used)
```

## Changes

### Executor code (`executors/claude-agent-sdk/`)
- `src/claude_agent_executor/executor.py` — Read `request.agent.prompt`; when non-empty, add `system_prompt={"type": "preset", "preset": "claude_code", "append": prompt}` to `ClaudeAgentOptions`.

### Tests (`executors/claude-agent-sdk/`)
- Update existing executor tests to verify `system_prompt` is set on `ClaudeAgentOptions` when `request.agent.prompt` is non-empty, and omitted when empty.

### Documentation (`executors/claude-agent-sdk/`)
- `README.md` — Document that the agent prompt is passed through to the Claude subprocess as appended system instructions.

## Non-goals

- Using the `description` field — stays metadata-only, consistent with the built-in executor where description is used for team orchestration and agent-as-tool, not system prompts.
- Replacing the SDK's built-in system prompt — the preset-with-append pattern ensures built-in tool instructions are always present.
- Prompt changes on session resume — the system prompt is set on `ClaudeAgentOptions` which applies to the session; resume behavior is out of scope.
- Changes to the ark-sdk or core operator — all changes are in the marketplace executor.
- Parameter templating in the executor — already handled upstream.
