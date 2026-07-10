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
  agent installs fine without it, but queries fail until it is present. Tool
  names carry the server's install name as a prefix, so install it as
  `kubernetes-mcp-server`. It is being migrated into the marketplace; until
  then, install the upstream chart with read-only RBAC on the Ark CRDs:

  ```bash
  helm install kubernetes-mcp-server \
    oci://ghcr.io/containers/charts/kubernetes-mcp-server \
    --version 0.1.0 \
    --namespace default \
    --set config.read_only=true \
    --set ingress.enabled=false \
    --set rbac.create=true \
    --set "rbac.extraRoles[0].name=ark-reader" \
    --set "rbac.extraRoles[0].namespace=default" \
    --set "rbac.extraRoles[0].rules[0].apiGroups[0]=ark.mckinsey.com" \
    --set "rbac.extraRoles[0].rules[0].resources={agents,teams,queries,models,mcpservers,a2aservers,a2atasks,tools,memories,executionengines,arkconfigs}" \
    --set "rbac.extraRoles[0].rules[0].verbs={get,list,watch}" \
    --set "rbac.extraRoleBindings[0].name=ark-reader" \
    --set "rbac.extraRoleBindings[0].namespace=default" \
    --set "rbac.extraRoleBindings[0].roleRef.name=ark-reader" \
    --wait --timeout=180s
  ```

  Then register it as an `MCPServer`:

  ```bash
  kubectl apply -f - <<'EOF'
  apiVersion: ark.mckinsey.com/v1alpha1
  kind: MCPServer
  metadata:
    name: kubernetes-mcp-server
    namespace: default
  spec:
    address:
      value: http://kubernetes-mcp-server.default.svc.cluster.local:8080/mcp
    description: k8s mcp server
    transport: http
    pollInterval: 10s
    timeout: 30s
  EOF
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
