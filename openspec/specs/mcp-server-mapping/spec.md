# MCP Server Mapping for Claude Agent SDK Executor

## ADDED Requirements

### Requirement: MCP servers from request are passed to the Claude SDK client
When `request.mcpServers` is non-empty, the executor SHALL map each `MCPServerConfig` into the `ClaudeAgentOptions.mcp_servers` dict and construct `allowed_tools` entries for each tool.

#### Scenario: Agent with MCP tools
- **WHEN** the executor receives a request with `mcpServers` containing one server "github-mcp" with transport "http", url "http://github-mcp:8080", and tools ["search_repos", "create_issue"]
- **THEN** the `ClaudeAgentOptions` SHALL include `mcp_servers={"github-mcp": {"type": "http", "url": "http://github-mcp:8080", "headers": {...}}}` and `allowed_tools` SHALL include `"mcp__github-mcp__search_repos"` and `"mcp__github-mcp__create_issue"`

#### Scenario: Agent with no MCP tools
- **WHEN** the executor receives a request with an empty `mcpServers` list
- **THEN** the `ClaudeAgentOptions` SHALL NOT include `mcp_servers` or `allowed_tools` and the executor SHALL behave identically to the current implementation

#### Scenario: Multiple MCP servers
- **WHEN** the executor receives a request with two servers in `mcpServers`
- **THEN** the `ClaudeAgentOptions.mcp_servers` dict SHALL contain entries for both servers and `allowed_tools` SHALL contain entries for all tools across both servers

### Requirement: Transport field is mapped correctly
The `MCPServerConfig.transport` field SHALL be mapped to the `type` key in the SDK's server config dict.

#### Scenario: HTTP transport
- **WHEN** `MCPServerConfig.transport` is `"http"`
- **THEN** the SDK server config SHALL have `"type": "http"`

#### Scenario: SSE transport
- **WHEN** `MCPServerConfig.transport` is `"sse"`
- **THEN** the SDK server config SHALL have `"type": "sse"`

### Requirement: Headers are passed through
Resolved headers from `MCPServerConfig.headers` SHALL be passed directly to the SDK server config's `headers` field.

#### Scenario: Server with auth headers
- **WHEN** `MCPServerConfig.headers` contains `{"Authorization": "Bearer token123"}`
- **THEN** the SDK server config SHALL have `"headers": {"Authorization": "Bearer token123"}`

#### Scenario: Server with no headers
- **WHEN** `MCPServerConfig.headers` is empty
- **THEN** the SDK server config SHALL have `"headers": {}`

### Requirement: Timeout field is dropped
The `MCPServerConfig.timeout` field SHALL NOT be mapped to the SDK config, as the Claude Agent SDK does not support per-server timeouts.

### Requirement: Servers with empty tool lists are skipped
If an `MCPServerConfig` has an empty `tools` list, that server SHALL be skipped entirely and not included in `mcp_servers`.

#### Scenario: Server with no tools
- **WHEN** `MCPServerConfig.tools` is an empty list
- **THEN** that server SHALL NOT appear in `ClaudeAgentOptions.mcp_servers`

### Requirement: Built-in tools remain available
The executor SHALL NOT set the `tools` parameter on `ClaudeAgentOptions`, ensuring all built-in tools (Read, Write, Edit, Bash, Grep, Glob) remain available alongside MCP tools.

### Requirement: MCP server connections are logged
When MCP servers are mapped, the executor SHALL log at INFO level which servers are being connected and how many tools each provides.

#### Scenario: Two servers connected
- **WHEN** two MCP servers are mapped with 3 and 1 tools respectively
- **THEN** the executor SHALL log a message indicating 2 MCP servers with their names and tool counts
