# Design: Agent CRD Prompt Support for Claude Agent SDK Executor

## Context

The executor receives `request.agent.prompt` (already parameter-templated by the ark-sdk query extension) but ignores it. The Claude subprocess runs with the SDK's default minimal system prompt regardless of what's configured on the Agent CRD.

The previous model-CRD-integration change explicitly deferred this as a non-goal because setting `system_prompt` as a plain string replaces the SDK's built-in prompt (which includes tool instructions). The SDK now supports a preset-with-append pattern that resolves this tension.

## Goals / Non-Goals

**Goals:**
- Pass the Agent CRD's resolved prompt to the Claude subprocess as appended system instructions
- Preserve the SDK's built-in system prompt (tool instructions, safety guidelines)
- No behavior change when the agent has no prompt configured

**Non-Goals:**
- Using `description` — stays metadata-only, consistent with the built-in executor
- Prompt changes on session resume — out of scope
- Parameter templating in the executor — handled upstream by ark-sdk
- Changes to ark-sdk or core operator

## Decisions

### Decision: Use preset-with-append for system prompt

The Claude Agent SDK's `system_prompt` parameter on `ClaudeAgentOptions` accepts three forms:

| Form | Effect |
|------|--------|
| `"custom string"` | Replaces the built-in prompt entirely |
| `{"type": "preset", "preset": "claude_code"}` | Uses the full Claude Code prompt, no customization |
| `{"type": "preset", "preset": "claude_code", "append": "..."}` | Full Claude Code prompt + custom text appended |

**Chosen**: Preset-with-append. This preserves built-in tool instructions while injecting the agent's persona.

**Alternative**: Plain string replacement. Rejected because losing tool instructions breaks built-in tool usage (Read, Write, Bash, etc.).

### Decision: Only set system_prompt when prompt is non-empty

When `request.agent.prompt` is empty (agent has no prompt configured), don't set `system_prompt` at all. This preserves current behavior exactly — the SDK uses its default minimal prompt.

### Decision: No composition with description

The `description` field is not included in the system prompt. In the built-in executor, description is used for team orchestration (selector agents, agent-as-tool) — not as system instructions. The Claude executor follows the same pattern.

## Risks / Trade-offs

**Prompt length** → Very long prompts appended to the Claude Code preset could approach context limits. Mitigation: This is the same risk as any system prompt — the SDK handles context management internally. No special handling needed.

**Preset stability** → The `"claude_code"` preset content may change across SDK versions. Mitigation: This is desirable — agents get improvements to tool handling automatically.
