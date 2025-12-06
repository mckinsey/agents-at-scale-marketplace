# Noah Service

ARK Runtime Administration Agent for infrastructure management.
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

# Uninstall Noah
helm uninstall noah -n default
```
