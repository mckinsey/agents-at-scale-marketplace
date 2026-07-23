# Argo Make Author

Conversational agent that authors Argo `WorkflowTemplate` resources composing
generic Argo steps with your existing Ark agents, models, and teams. It grounds
every query target on the live cluster and refuses to reference resources it
cannot find.

This is a manifest-only agent: the chart deploys a single `Agent` custom
resource. It ships without a model and references the read-only
`kubernetes-mcp-server` tools for cluster grounding.

## Prerequisites

- **A model.** The agent ships without one. Set `agent.modelRef` at install
  time, or assign a model afterwards. Queries fail until a model is set.

  ```bash
  helm install argo-make-author ./chart -n default --set agent.modelRef=default
  ```

- **kubernetes-mcp-server.** The `kubernetes-mcp-server-resources-list` and
  `-resources-get` tools come from the in-cluster `kubernetes-mcp-server`. The
  agent installs fine without it, but queries fail until it is present. Install
  the marketplace chart, which ships read-only mode, the ark-reader RBAC (Ark
  CRDs + Argo workflows/workflow templates), and the `MCPServer` registration:

  ```bash
  ark install marketplace/mcps/kubernetes-mcp-server
  ```

  Or with Helm directly:

  ```bash
  helm install kubernetes-mcp-server \
    oci://ghcr.io/mckinsey/agents-at-scale-marketplace/charts/kubernetes-mcp-server \
    -n default
  ```

## Quickstart

### Using Ark CLI

```bash
ark install marketplace/agents/argo-make-author
```

### Using DevSpace

```bash
cd agents/argo-make-author
devspace deploy
```

### Using Helm

```bash
# Install to cluster
helm install argo-make-author ./chart -n default

# Uninstall
helm uninstall argo-make-author -n default
```

## Configuration

| Value                   | Default                                  | Description                                             |
| ----------------------- | ---------------------------------------- | ------------------------------------------------------- |
| `agent.name`            | `argo-make-author`                       | Name of the `Agent` resource.                           |
| `agent.modelRef`        | `""`                                     | Model to assign. Empty ships the agent without a model. |
| `mcp.resourcesListTool` | `kubernetes-mcp-server-resources-list`   | MCP tool used to list cluster resources.                |
| `mcp.resourcesGetTool`  | `kubernetes-mcp-server-resources-get`    | MCP tool used to read a single resource.                |
