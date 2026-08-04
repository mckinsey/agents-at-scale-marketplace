# Argo Workflow Runner

Ark HTTP tools that **run** Argo workflows without letting a model define one.
Three standalone `Tool` custom resources call the Argo Workflows API server to:

- **submit** an existing `WorkflowTemplate` by name,
- **retry** an existing `Workflow` in place,
- **resubmit** an existing `Workflow` as a fresh run.

There is no MCP server and no image - just `Tool` CRDs (`spec.type: http`) that
any agent can attach through `spec.tools`. This is the "run" counterpart to
`agents/argo-make-author`, which only authors templates.

## Why it cannot run arbitrary workflows

The security boundary is the set of endpoints these tools call, not a prompt:

1. Only `submit`, `retry`, and `resubmit` are ever called. The create-Workflow
   endpoint (`POST /api/v1/workflows/{namespace}`), which accepts a full
   `Workflow` manifest, is never exposed.
2. `resourceKind` is a literal `WorkflowTemplate` baked into the submit body. A
   model cannot change it, so it cannot submit an arbitrary `Workflow` or
   `CronWorkflow` kind either.
3. The target namespace is fixed at install time (`argoServer.namespace`), never
   a model argument, so the tools cannot reach resources in other namespaces.
4. As an outer backstop, scope the bearer token's RBAC in the cluster: grant the
   argo-server service account only `create` on `workflows` and `get` / `list`
   on `workflowtemplates` in the target namespace. RBAC lives with the Argo
   install, not this chart.

The model only supplies the name of an already-existing resource plus launch
options - never a spec.

## Prerequisites

- **Argo Workflows with the API server enabled.** This chart does not install
  Argo; it is a cluster prerequisite. The tools call `argoServer.baseUrl`.
- **An authentication token** for the Argo API server (see below).

## Tools

| Tool                             | Method & endpoint                                   | Inputs                          |
| -------------------------------- | --------------------------------------------------- | ------------------------------- |
| `argo-submit-workflow-template`  | `POST .../workflows/<ns>/submit`                    | `name`, `parameters`            |
| `argo-retry-workflow`            | `PUT .../workflows/<ns>/<name>/retry`               | `name`, `restartSuccessful`     |
| `argo-resubmit-workflow`         | `PUT .../workflows/<ns>/<name>/resubmit`            | `name`, `memoized`              |

### `parameters` format (submit)

`parameters` is a **JSON array of `key=value` strings** for the template's
`spec.arguments.parameters`, for example:

```json
["risk-level=high", "mode=sequential"]
```

Use `[]` (the default) to accept the template's declared defaults.

## Quickstart

### Using Ark CLI

```bash
ark install marketplace/tools/argo-workflow-runner
```

### Using DevSpace

```bash
cd tools/argo-workflow-runner
devspace deploy
```

### Using Helm

```bash
# Install, letting the chart create the auth Secret from a token
helm install argo-workflow-runner ./chart -n default \
  --set auth.token=<argo-api-token>

# Uninstall
helm uninstall argo-workflow-runner -n default
```

If you manage the auth Secret yourself, leave `auth.token` empty and point
`auth.secretName` / `auth.key` at your Secret. The referenced value must be the
**complete** `Authorization` header, including the `Bearer ` prefix (Ark HTTP
tools send the header value verbatim).

## Configuration

| Value                   | Default                                             | Description                                                              |
| ----------------------- | --------------------------------------------------- | ------------------------------------------------------------------------ |
| `argoServer.baseUrl`    | `https://argo-server.argo.svc.cluster.local:2746`   | Argo API server base URL. Only submit/retry/resubmit endpoints are hit.  |
| `argoServer.namespace`  | `""`                                                | Namespace the tools act in. Empty defaults to the release namespace.     |
| `auth.secretName`       | `argo-workflow-runner-auth`                         | Secret holding the `Authorization` header value.                         |
| `auth.key`              | `authorization`                                     | Key within that Secret.                                                  |
| `auth.token`            | `""`                                                | If set, the chart creates the Secret holding `Bearer <token>`.           |
| `tools.submitName`      | `argo-submit-workflow-template`                     | Name of the submit `Tool` resource.                                      |
| `tools.retryName`       | `argo-retry-workflow`                               | Name of the retry `Tool` resource.                                       |
| `tools.resubmitName`    | `argo-resubmit-workflow`                            | Name of the resubmit `Tool` resource.                                    |
| `timeout`               | `30s`                                               | Per-request timeout applied to every tool.                              |

## TLS

Argo's API server defaults to HTTPS with a **self-signed** certificate, and
Ark's HTTP tool has no skip-verify option. Choose one of:

- point `argoServer.baseUrl` at an endpoint presenting a **trusted** certificate,
- terminate TLS in-cluster in front of argo-server, or
- run argo-server with `--secure=false` and use a plain `http://...:2746` URL
  reachable only inside the cluster network.

## Attaching to an agent

Reference the tool names in an agent's `spec.tools`:

```yaml
apiVersion: ark.mckinsey.com/v1alpha1
kind: Agent
metadata:
  name: workflow-operator
spec:
  tools:
    - type: custom
      name: argo-submit-workflow-template
    - type: custom
      name: argo-retry-workflow
    - type: custom
      name: argo-resubmit-workflow
```
