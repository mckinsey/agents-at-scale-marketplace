# MCP Server Support for Claude Agent SDK Executor

## Problem

The Claude Agent SDK executor ignores MCP tools assigned to agents. When an agent has MCP-type tools in its spec, the executor receives them via `request.mcpServers` (after the upstream ark-sdk change) but does nothing with them — the Claude subprocess only has access to its built-in tools (Read, Write, Edit, Bash, Grep, Glob).

The Claude Agent SDK natively supports MCP server connections via `ClaudeAgentOptions.mcp_servers`, and the data shape from Ark's `MCPServerConfig` maps nearly 1:1 to the SDK's expected format. The integration is straightforward.

## Solution

Map `request.mcpServers` from the `ExecutionEngineRequest` into `ClaudeAgentOptions.mcp_servers` and `allowed_tools` when constructing the Claude SDK client. Built-in tools remain available alongside MCP tools.

### Mapping

```
Ark MCPServerConfig           →  ClaudeAgentOptions
────────────────────              ────────────────────
name: "github-mcp"           →  key in mcp_servers dict
url: "http://..."            →  "url": "http://..."
transport: "http"            →  "type": "http"
headers: {"Auth": "Bearer…"} →  "headers": {"Auth": "Bearer…"}
tools: ["search_repos"]      →  allowed_tools: ["mcp__github-mcp__search_repos"]
timeout: "30s"               →  (dropped — SDK uses 60s default, no per-server config)
```

### Behavior

- **No MCP tools assigned**: Executor behaves exactly as today — built-in tools only.
- **MCP tools assigned**: Built-in tools remain available; MCP servers are connected and their tools are pre-approved via `allowed_tools` using the `mcp__{server}__{tool}` naming convention.
- **MCP server resolution failure**: Handled upstream in the ark-sdk query extension (servers that fail to resolve are skipped with a warning before reaching the executor).

## Changes

### Executor code (`executors/claude-agent-sdk/`)
- `src/claude_agent_executor/executor.py` — Add a helper to map `List[MCPServerConfig]` to the SDK's `mcp_servers` dict and `allowed_tools` list. Wire into `ClaudeAgentOptions` construction in `execute_agent()`.

### Documentation (`executors/claude-agent-sdk/`)
- `README.md` — Add MCP tools section showing an agent spec with MCP tools assigned, and mention that MCP tools are passed through to the Claude subprocess.

### Documentation (`docs/content/executors/`)
- `claude-agent-sdk.mdx` — Update Overview to mention MCP tool support. Add section explaining how MCP servers are connected, the allowlist pattern, and an example agent spec with tools.

## Dependencies

- **Upstream**: Requires the ark-sdk `MCPServerConfig` / `mcpServers` change from `ark/bravo`. For **development and testing**, the DevSpace dev pipeline live-syncs the local ark-sdk source (`~/ws/agents-at-scale-ark/lib/ark-sdk/`) into the pod, so the new types are available immediately without waiting for a release. For **production**, the ark-sdk package must be released with the change.

## Non-goals

- New CRDs or changes to existing CRDs — this reuses the existing MCPServer and Tool CRDs unchanged (resolution logic is in [ark#1459](https://github.com/mckinsey/agents-at-scale-ark/pull/1459))
- Changes to the ark-sdk (handled in separate change in bravo repo)
- Support for non-MCP tool types (http, agent, team, builtin) — these are excluded by the ark-sdk
- Per-server timeout configuration (SDK doesn't expose this)
- Changes to session management or built-in tool behavior
