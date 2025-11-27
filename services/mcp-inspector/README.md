# MCP Inspector

Developer tool for testing and debugging MCP servers in Kubernetes.

## Quickstart

### Using DevSpace

```bash
# Deploy + show access URLs
devspace dev

# Deploy MCP Inspector
devspace deploy

# Uninstall MCP Inspector
devspace purge
```

### Using Helm

```bash
# Install MCP Inspector to cluster
helm install mcp-inspector ./chart -n default

# Uninstall MCP Inspector
helm uninstall mcp-inspector -n default

# Port-forward to access locally
kubectl port-forward -n default svc/mcp-inspector 6274:6274
```

## Usage

1. Access the UI at http://mcp-inspector.default.127.0.0.1.nip.io:8080
2. Go to "Configuration" and set "Proxy Session Token" to any value (e.g., `test`)
3. Find available MCP servers:
   ```bash
   kubectl get mcpserver -A
   # NAMESPACE   NAME                 TOOLS   PHASE   ADDRESS
   # default     ark-admin-mcp        7       ready   http://ark-admin-mcp.default.svc.cluster.local:8080/mcp
   ```
4. Connect using the server address

## Configuration

- **Namespace**: `default`
- **Client Port**: `6274`
- **Proxy Port**: `6277`
