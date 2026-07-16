# Kubernetes MCP Server

Read-only [kubernetes-mcp-server](https://github.com/containers/kubernetes-mcp-server) registered with Ark for grounding agents on cluster resources. Wraps the upstream chart and layers Ark configuration: read-only mode, namespace-scoped read-only RBAC, a `localhost-gateway` HTTPRoute, and an Ark `MCPServer` registration.

## Quickstart

```bash
# Deploy with Helm
helm install kubernetes-mcp-server ./chart -n default --create-namespace

# Verify
kubectl get mcpserver kubernetes-mcp-server
```

**Using DevSpace (for development):**

```bash
cd mcps/kubernetes-mcp-server
devspace deploy
```

## What it deploys

- The upstream `kubernetes-mcp-server` chart from `oci://ghcr.io/containers/charts`, in read-only mode. Only `resources_list` / `resources_get` are exposed.
- A namespace-scoped read-only `Role`/`RoleBinding` (`ark-reader`) granting `get`/`list`/`watch` on `ark.mckinsey.com` resources and `argoproj.io` workflows / workflow templates.
- A `localhost-gateway` `HTTPRoute` (`kubernetes-mcp-server.127.0.0.1.nip.io`), with Ingress disabled.
- An Ark `MCPServer` resource so the server's tools are discovered. The address defaults to the in-cluster service of this release, so the chart is namespace-portable.

## Configuration

Helm chart options (`chart/values.yaml`):

- `kubernetes-mcp-server.config.read_only`: read-only mode (default `true`).
- `kubernetes-mcp-server.rbac.extraRoles`: read-only roles granted to the server.
- `kubernetes-mcp-server.httpRoute`: Gateway API routing configuration.
- `mcpServer.create`: register the Ark `MCPServer` (default `true`).
- `mcpServer.address`: override the server address (defaults to the in-cluster service).

## Using with Ark

The chart registers an `MCPServer` named `kubernetes-mcp-server`, which auto-generates `Tool` resources. Reference them from an agent:

```yaml
apiVersion: ark.mckinsey.com/v1alpha1
kind: Agent
metadata:
  name: cluster-inspector
spec:
  tools:
    - name: kubernetes-mcp-server-resources-list
      type: custom
    - name: kubernetes-mcp-server-resources-get
      type: custom
```
