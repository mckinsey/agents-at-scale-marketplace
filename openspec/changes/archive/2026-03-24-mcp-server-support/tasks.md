## 1. Executor Code

- [x] 1.1 Add `_build_mcp_options()` helper method to `ClaudeAgentExecutor` in `executor.py` that maps `List[MCPServerConfig]` to a `mcp_servers` dict and `allowed_tools` list. Skip servers with empty tool lists. Map `transport` → `type`.
- [x] 1.2 Wire `_build_mcp_options()` into `execute_agent()` — call it with `request.mcpServers`, spread results into `ClaudeAgentOptions` constructor. Only pass `mcp_servers` and `allowed_tools` when non-empty.
- [x] 1.3 Add INFO-level logging when MCP servers are connected: server names and tool counts.

## 2. Tests

- [x] 2.1 Add test for `_build_mcp_options()` with a single server — verify `mcp_servers` dict shape, `type` mapping, headers passthrough, `allowed_tools` entries.
- [x] 2.2 Add test for multiple servers — verify all servers present in dict and all tools in `allowed_tools`.
- [x] 2.3 Add test for empty `mcpServers` list — verify no `mcp_servers` or `allowed_tools` returned.
- [x] 2.4 Add test for server with empty tools list — verify server is skipped.
- [x] 2.5 Add test for `execute_agent` integration — mock `ClaudeSDKClient` and verify `ClaudeAgentOptions` is constructed with correct `mcp_servers` and `allowed_tools` when request has MCP servers.

## 3. Documentation — README

- [x] 3.1 Update `executors/claude-agent-sdk/README.md` — add "MCP Tools" section after "How It Works" showing an example agent spec with MCP tools assigned, and a brief explanation that MCP tools are passed through to the Claude subprocess alongside built-in tools.

## 4. Documentation — MDX Guide

- [x] 4.1 Update `docs/content/executors/claude-agent-sdk.mdx` Overview bullet list — add "MCP Tool Support" bullet mentioning that MCP servers assigned to the agent are connected automatically.
- [x] 4.2 Add "MCP Tools" section to `claude-agent-sdk.mdx` (after "Session Behavior") covering: how MCP servers are connected, the allowlist pattern, that built-in tools remain available, and an example agent spec with Tool and MCPServer CRDs.
