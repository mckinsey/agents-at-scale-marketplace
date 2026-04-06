## Why

The Claude Code executor runs as a single Deployment — all sessions share the same pod. Claude Agent SDK sessions need filesystem access (git repos, workspace files), and concurrent sessions on a shared pod fight over locks, ports, and workspace state.

Session scheduling lets the executor create a dedicated sandbox per session using [`kubernetes-sigs/agent-sandbox`](https://github.com/kubernetes-sigs/agent-sandbox). Each session gets its own pod with its own PVC, stable DNS, and network isolation.

## Design Principle

Use `kubernetes-sigs/agent-sandbox` (v0.2.1, SIG Apps) rather than building custom pod lifecycle management. agent-sandbox provides a `Sandbox` CRD purpose-built for isolated, stateful, singleton workloads — exactly our use case. It handles pod lifecycle, persistent storage, stable DNS, network isolation, warm pools, and reconciliation.

Where agent-sandbox doesn't cover our needs (idle TTL), we layer minimal executor logic on top. Configuration follows the Argo Workflows convention of a conventionally-named ConfigMap.

## What Changes

### ExecutionEngine CRD

No CRD changes. Session scheduling is an executor concern, not a platform concern.

### Prerequisites

agent-sandbox must be installed in the cluster:

```bash
export VERSION="v0.2.1"
kubectl apply -f https://github.com/kubernetes-sigs/agent-sandbox/releases/download/${VERSION}/manifest.yaml
kubectl apply -f https://github.com/kubernetes-sigs/agent-sandbox/releases/download/${VERSION}/extensions.yaml
```

### Executor Configuration

Follows the Argo Workflows pattern — conventionally-named ConfigMap (`executor-claude-agent-config`), overridable via `EXECUTOR_CONFIG_MAP` env var.

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: executor-claude-agent-config
data:
  # "none": single pod (current behavior).
  # "sandbox": create a Sandbox CR per session via agent-sandbox.
  scheduling: "sandbox"

  # How long after the last A2A message before shutdown.
  # The executor rolls forward the Sandbox's spec.shutdownTime on each message.
  sessionIdleTTL: "24h"

  # Maps to agent-sandbox shutdownPolicy: "Delete" (default) or "Retain".
  shutdownPolicy: "Delete"

  # Standard agent-sandbox SandboxSpec. The image must run the A2A server.
  sandboxSpec: |
    podTemplate:
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
    volumeClaimTemplates:
      - metadata:
          name: workspace
        spec:
          accessModes:
            - ReadWriteOnce
          resources:
            requests:
              storage: 10Gi
```

### Executor Behavior

**scheduling: none (default):** Current behavior. Single pod, all sessions share it.

**scheduling: sandbox:** When the executor receives an A2A conversation:

1. **Check for existing Sandbox.** Label selector: `ark.mckinsey.com/session-id={sessionId}`.
2. **If none exists**, render `sandboxSpec` and create a `Sandbox` CR with `shutdownTime` set to `now + sessionIdleTTL`.
3. **Wait for Ready condition** on the Sandbox CR.
4. **Proxy the A2A message** to `session-{sessionId}.{namespace}.svc.cluster.local:8000` (stable DNS from agent-sandbox).
5. **Roll forward `shutdownTime`** on each message.
6. **On expiry**, agent-sandbox controller handles cleanup based on `shutdownPolicy`.

### Warm Pool (optional)

For faster session startup, deploy a `SandboxTemplate` and `SandboxWarmPool`. The executor creates a `SandboxClaim` instead of a `Sandbox`, claiming a pre-warmed pod from the pool.

### RBAC

The executor needs Sandbox/SandboxClaim CRUD permissions. Pod and PVC management is handled by the agent-sandbox controller.

## What We Get from agent-sandbox

| Concern | agent-sandbox |
|---|---|
| Pod lifecycle | Sandbox controller |
| Crash recovery | Controller reconciliation |
| Persistent storage | `volumeClaimTemplates` |
| Stable networking | Service + DNS per Sandbox |
| Warm pools | `SandboxWarmPool` + `SandboxClaim` |
| Network isolation | Managed NetworkPolicy |
| Pause/resume | `replicas: 0/1` |
| Shutdown | `shutdownTime` + `shutdownPolicy` |

## Impact

- `services/executor-claude-agent/src/` — sandbox creation, ConfigMap watcher, A2A proxy logic
- `services/executor-claude-agent/chart/` — RBAC for Sandbox CRs, ConfigMap template, agent-sandbox dependency
- No changes to the Ark core repo or ExecutionEngine CRD

## Non-goals

- Lifecycle hooks via init containers (follow-on story)
- Custom SandboxTemplate + NetworkPolicy configuration (follow-on)
- Implementation roadmap / phasing
