# Noah Service

ARK Runtime Administration Agent with full cluster privileges for infrastructure management.
Provides an MCP server with runtime administration tools and a conversational agent interface.

## Quickstart

### Using DevSpace

```bash
# Deploy Noah with hot reloading
devspace dev

# Deploy Noah (production build)
devspace deploy

# Uninstall Noah
devspace purge
```

### Using Helm

```bash
# Install Noah to cluster
helm install noah ./chart -n default

# Install with HTTPRoute enabled (requires Gateway API)
helm install noah ./chart -n default \
  --set httpRoute.enabled=true

# Uninstall Noah
helm uninstall noah -n default
```

## Tools Provided

- `kubectl` - Kubernetes cluster management commands
- `helm` - Package management and chart operations
- `bash` - System commands for advanced operations
- `python` - Python code execution
- `ark_status` - Check ARK system status and version
- `aas_runtime_101` - AAS runtime resource discovery and operational procedures
- `system_info` - MCP server capabilities report

## Usage

Once deployed, Noah can be accessed through ARK as the runtime administration agent.

### Example Interactions

- "Show me all pods in the cluster"
- "Check the status of ARK services"
- "Run a Python script to analyze resource usage"
- "Deploy a new Helm chart"

## Security

⚠️ **Warning**: Noah has cluster-admin privileges and can perform any operation in the cluster. Always confirm destructive operations before execution.

## Notes

- Deploys as both an Agent and MCPServer resource
- Requires RBAC permissions (ClusterRole and ServiceAccount)
- Default namespace: `default`