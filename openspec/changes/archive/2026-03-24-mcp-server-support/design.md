# Design: MCP Server Support for Claude Agent SDK Executor

## Context

The Claude Agent SDK executor currently only uses built-in tools (Read, Write, Edit, Bash, Grep, Glob). The upstream ark-sdk change (bravo repo: `mcp-tools-for-named-executors`) replaces the flat `tools: List[ToolDefinition]` field on `ExecutionEngineRequest` with `mcpServers: List[MCPServerConfig]`, providing resolved MCP server connection info grouped by server.

The Claude Agent SDK natively supports MCP server connections via `ClaudeAgentOptions.mcp_servers`. The data shapes are nearly identical — this is a mapping exercise, not an architectural change.

## Goals / Non-Goals

**Goals:**
- Map Ark's `MCPServerConfig` to the Claude SDK's `mcp_servers` format
- Pre-approve MCP tools via `allowed_tools` using the SDK's `mcp__{server}__{tool}` naming convention
- Keep all built-in tools available alongside MCP tools
- Document the feature for executor users

**Non-Goals:**
- ark-sdk changes (separate change, bravo repo)
- Per-server timeout support (SDK doesn't expose this)
- Non-MCP tool types (excluded by ark-sdk before reaching executor)
- Changes to session management, OTEL, or built-in tool behavior

## Decisions

### Decision: Map at the executor level, not in a shared utility

Build the mapping inline in `executor.py` as a private helper method on `ClaudeAgentExecutor`. The mapping is Claude-SDK-specific (field names, `mcp__` naming convention, transport field rename) and not reusable by other executors.

Alternative considered: Shared utility in a common module. Rejected because each executor's MCP client integration is different — LangChain would have its own mapping to LangChain's MCP client, CrewAI to CrewAI's, etc.

### Decision: Use `allowed_tools` for the MCP tool allowlist

The SDK has two relevant options:
- `tools`: Controls which *built-in* tools are available. MCP tools are unaffected.
- `allowed_tools`: Pre-approves tools for automatic use without permission prompts.

We use `allowed_tools` with `mcp__{server}__{tool}` patterns to pre-approve exactly the tools the agent references. This enforces Ark's agent-level tool scoping inside the Claude subprocess.

We do NOT set `tools` — leaving it unset preserves all built-in tools at their defaults.

### Decision: Drop the `timeout` field silently

Ark's `MCPServerConfig` includes a `timeout` field. The Claude Agent SDK does not expose per-server timeout configuration (it uses a 60s default internally). We drop this field during mapping.

Alternative considered: Log a warning when timeout is present. Rejected because timeout is always present on every MCPServerConfig — logging on every server every request would be noise, not signal.

### Decision: Skip servers with empty tool lists

If an `MCPServerConfig` arrives with an empty `tools` list (possible if all tools were filtered out upstream), skip connecting to that server entirely. No point establishing an MCP connection for zero tools.

### Decision: Log MCP server connections at INFO level

Log which MCP servers are being connected and how many tools each provides. This is useful for debugging without being noisy — it happens once per request, and MCP tools are an explicit configuration choice.

```
Connecting 2 MCP servers: github-mcp (3 tools), slack-mcp (1 tool)
```

## Data Flow

```
ExecutionEngineRequest                    ClaudeAgentOptions
─────────────────────                     ──────────────────

mcpServers: [                             mcp_servers={
  MCPServerConfig(                          "github-mcp": {
    name="github-mcp",                       "type": "http",
    url="http://github-mcp:8080",            "url": "http://github-mcp:8080",
    transport="http",                        "headers": {
    headers={"Authorization":                  "Authorization": "Bearer xxx"
             "Bearer xxx"},                  }
    tools=["search_repos",                 },
           "create_issue"],                 "slack-mcp": {
    timeout="30s"                            "type": "sse",
  ),                                         "url": "http://slack-mcp:8080/sse",
  MCPServerConfig(                           "headers": {}
    name="slack-mcp",                      }
    url="http://slack-mcp:8080/sse",     }
    transport="sse",
    headers={},                           allowed_tools=[
    tools=["send_message"],                 "mcp__github-mcp__search_repos",
    timeout="30s"                           "mcp__github-mcp__create_issue",
  )                                         "mcp__slack-mcp__send_message",
]                                         ]
```

## Risks / Trade-offs

**Upstream dependency** → Requires the ark-sdk `MCPServerConfig` change from bravo. DevSpace dev mode live-syncs the local ark-sdk source into the pod (`devspace.yaml` line 50), so development and integration testing can proceed immediately against the local bravo checkout. Only the production release requires a published ark-sdk version.

**Transport value mismatch** → Ark uses `transport: "http"` or `"sse"`. The Claude SDK expects `type: "http"` or `"sse"`. The field is renamed during mapping. If either side introduces new transport types, the mapping needs updating.

**SDK MCP connection failures at runtime** → If the Claude subprocess can't connect to an MCP server (network issue, server down), the SDK handles this internally — it logs the failure and continues without those tools. This is acceptable behavior; the agent degrades gracefully.
