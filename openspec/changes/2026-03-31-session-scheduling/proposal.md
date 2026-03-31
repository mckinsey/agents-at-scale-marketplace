## Why

The Claude Code executor runs as a single Deployment — all sessions share the same pod. Claude Agent SDK sessions need filesystem access (git repos, workspace files), and concurrent sessions on a shared pod fight over locks, ports, and workspace state.

Session scheduling lets the executor create a dedicated Deployment per session. Each session gets its own pod with its own PVC, eliminating contention.

## Design Principle

Follow conventions from common Kubernetes projects, in particular Argo Workflows. Argo solves a similar problem — scheduling workflow pods from a WorkflowTemplate. A session for an agent is analogous to a workflow for a template. Where Argo has an established pattern (conventional ConfigMap names, volumeClaimTemplates, direct pod IP communication), we use it.

The executor remains a service (FastAPI, A2A endpoint), but with session scheduling it also behaves like an operator — it watches a ConfigMap for configuration and schedules child resources (Deployments, PVCs) in response to incoming sessions. Similar to how the Argo workflow-controller is a service that manages workflow pod lifecycles.

## What Changes

### ExecutionEngine CRD

No CRD changes. Session scheduling is an executor concern, not a platform concern.

### Executor Configuration

Inspired by Argo Workflows, where the workflow-controller reads a conventionally-named ConfigMap (`workflow-controller-configmap`). Argo allows overriding the name via the `--configmap` CLI flag.

We follow the same pattern:

- **Default ConfigMap name:** `executor-claude-agent-config` (convention, matches the Deployment name)
- **Override via env var:** `EXECUTOR_CONFIG_MAP` on the executor Deployment

The executor reads this ConfigMap at startup and watches it for changes.

### ConfigMap Schema

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: executor-claude-agent-config
data:
  # Scheduling mode.
  # "none": single pod, all sessions share it (current behavior).
  # "session": apply the session template below to create a dedicated
  #   Deployment per session.
  scheduling: "session"

  # How long after the last A2A message before the session's Deployment
  # is deleted. The executor resets this timer on each message.
  sessionExpiryTTL: "24h"

  # When to delete PVCs created from volumeClaimTemplates.
  # Follows Argo Workflows' volumeClaimGC.strategy convention
  # (OnWorkflowCompletion / OnWorkflowSuccess). Sessions don't have a
  # completion event — they expire via TTL — so the strategies are:
  #   "OnSessionExpiry" (default): delete PVCs when the session TTL
  #     expires, along with the Deployment.
  #   "Never": retain PVCs after session cleanup. Useful for debugging
  #     or resuming sessions against the same workspace.
  # The executor identifies which PVCs to delete via the
  # ark.mckinsey.com/session-id label — all session resources
  # (Deployments, PVCs) share this label.
  volumeClaimGC: "OnSessionExpiry"

  # Session template. Applied once per session when scheduling is
  # "session". Contains a Deployment spec and optional volumeClaimTemplates,
  # following the Argo Workflows pattern where volumeClaimTemplates sit
  # alongside the pod template, linked by volume name.
  #
  # Template rendering:
  #   The executor renders Go template variables before applying:
  #     {{.SessionID}}  — unique session identifier
  #     {{.EngineName}} — ExecutionEngine resource name
  #     {{.Namespace}}  — ExecutionEngine namespace
  #
  # Labels and ownership:
  #   The executor adds to every resource it creates:
  #     label: ark.mckinsey.com/session-id={{.SessionID}}
  #     label: ark.mckinsey.com/engine={{.EngineName}}
  #     ownerReferences: pointing to the ExecutionEngine resource
  #
  # Validation:
  #   The executor validates the deployment against the Kubernetes API
  #   schema before applying.
  #
  # Networking:
  #   No Service is created. The executor finds session pods by label
  #   and communicates via pod IP + containerPort — same pattern as Argo
  #   Workflows, which talks to workflow step pods directly without
  #   creating Services.
  #
  # Volume binding:
  #   When volumeClaimTemplates is present, the executor creates the
  #   PVC and injects a matching entry into the Deployment's
  #   spec.template.spec.volumes, linking it to the container's
  #   volumeMounts by name ("workspace" in the example below).
  sessionTemplate: |
    deployment:
      apiVersion: apps/v1
      kind: Deployment
      metadata:
        name: session-{{.SessionID}}
      spec:
        replicas: 1
        selector:
          matchLabels:
            ark.mckinsey.com/session-id: "{{.SessionID}}"
        template:
          metadata:
            labels:
              ark.mckinsey.com/session-id: "{{.SessionID}}"
              ark.mckinsey.com/engine: "{{.EngineName}}"
          spec:
            containers:
              - name: claude-agent
                image: ghcr.io/mckinsey/executor-claude-agent:latest
                ports:
                  - containerPort: 8000
                resources:
                  requests:
                    memory: "512Mi"
                    cpu: "250m"
                  limits:
                    memory: "2Gi"
                    cpu: "1000m"
                volumeMounts:
                  - name: workspace
                    mountPath: /workspace

    # PVC templates created per session, linked to the Deployment by
    # volume name. The name "workspace" here matches the volumeMounts
    # name in the container above. The executor creates the PVC, adds
    # it to the Deployment's volumes, and binds them — same as
    # StatefulSet and Argo Workflows volumeClaimTemplates.
    volumeClaimTemplates:
      - metadata:
          name: workspace
        spec:
          accessModes:
            - ReadWriteOnce
          resources:
            requests:
              storage: 10Gi

    # --- Alternative: attach an existing PVC instead of creating one ---
    #
    # To use a pre-existing PVC (e.g. a shared dataset or pre-provisioned
    # volume), omit volumeClaimTemplates and reference the PVC directly
    # in the Deployment's volumes. The executor will not create or delete
    # the PVC — volumeClaimGC only applies to PVCs created from
    # volumeClaimTemplates.
    #
    # deployment:
    #   ...
    #   spec:
    #     template:
    #       spec:
    #         containers:
    #           - name: claude-agent
    #             volumeMounts:
    #               - name: workspace
    #                 mountPath: /workspace
    #         volumes:
    #           - name: workspace
    #             persistentVolumeClaim:
    #               claimName: my-existing-pvc
```

### Executor Behavior

**scheduling: none (default):** Current behavior. Single Deployment, all sessions share it. The executor handles requests directly via `/execute`.

**scheduling: session:** When the executor receives an A2A conversation:

1. **Check for existing session.** Label selector: `ark.mckinsey.com/session-id={sessionId}`.
2. **If none exists**, render `sessionTemplate`, validate against K8s API schema, and apply:
   - PVCs from `volumeClaimTemplates` (if present), linked to the Deployment by volume name
   - Deployment from `deployment`, with PVC volume injected
   - All resources get ownerReferences and session labels
3. **Find the session pod** by label, get its IP from Pod status, proxy the A2A message to `{podIP}:{containerPort}`.
4. **Wait for readiness** if the pod is not yet ready — watch `Deployment.status.readyReplicas`.
5. **Reset the TTL timer** on each message.
6. **On TTL expiry:**
   - Delete the Deployment (label selector: `ark.mckinsey.com/session-id`)
   - If `volumeClaimGC` is `OnSessionExpiry`, also delete PVCs with the same label
   - If `volumeClaimGC` is `Never`, PVCs are retained

### RBAC

The executor needs permissions to create/delete Deployments, read Pods (for IP and status), and create/delete PVCs. Document in the Helm chart with comments explaining why.

## Impact

- `services/executor-claude-agent/src/` — session scheduling logic, ConfigMap watcher, template renderer
- `services/executor-claude-agent/chart/` — RBAC roles, ConfigMap template, env var for config override
- No changes to the Ark core repo or ExecutionEngine CRD

## Non-goals

- Lifecycle hooks via init containers (follow-on story)
- Network policies
- Integration test port collisions (separate bug)
- Implementation roadmap / phasing
