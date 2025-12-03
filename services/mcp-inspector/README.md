# MCP Inspector

Debug and test MCP servers in Kubernetes.

## Install

```bash
ark install marketplace/services/mcp-inspector
```

Or with DevSpace:

```bash
devspace dev
```

## Access

Dashboard URL:
```
http://mcp-inspector.default.127.0.0.1.nip.io:8080/?MCP_PROXY_FULL_ADDRESS=http://mcp-inspector-proxy.default.127.0.0.1.nip.io:8080
```

## Usage

1. Go to Configuration and set Proxy Session Token to `test`
2. Connect to an MCP server: `kubectl get mcpserver -A`
