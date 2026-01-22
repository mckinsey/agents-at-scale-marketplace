# Implementation: Claude Code Marketplace Integration


## 1. Objective

Package Claude Code agent as a Helm chart in the marketplace to enable one-command installation:

```bash
ark install marketplace/claude-code
```

**Technical Context**:
- ARK Controller already supports `type: pod` agents (no controller changes needed)
- Marketplace CI/CD auto-detects new agents and publishes to GHCR
- Agent executes via pod lifecycle: create → logs → JQ filter → cleanup

---

## 2. Dependencies

### 2.1 Dependencies required (Already Available)

| Dependency | Location | Status |
|------------|----------|--------|
| ARK Controller | `mckinsey/ark` | Pod agent support in mainline |
| Marketplace CI/CD | `.github/workflows/` | Auto-detects `agents/` directory |
| Dockerfile | `ark/agents/claude-code/Dockerfile` | Tested and working |
| Agent manifest | `ark/agents/claude.yaml` | Reference implementation |

---

## 3. Implementation Steps

The central idea is to move the claude-code agent from `ark/agents/claude-code` to the Marketplace repository.

### Step 1: Create Directory Structure

Create the following directory tree in `agents-at-scale-marketplace/`:

```
agents/claude-code/
├── Dockerfile
├── CHANGELOG.md
├── README.md
└── chart/
    ├── Chart.yaml
    ├── values.yaml
    └── templates/
        ├── _helpers.tpl
        ├── secret.yaml
        ├── pvc.yaml
        └── agent.yaml
```

### Step 2: Copy and Adapt Dockerfile

**Source**: `ark/agents/claude-code/Dockerfile`  
**Destination**: `agents/claude-code/Dockerfile`

**Action**: Copy as-is (no modifications needed)

**What it contains**:
- Node.js 22 base image
- Claude Code CLI via NPM
- Non-root user setup

**Note**: Dockerfile includes private plugin installation via `GITHUB_TOKEN`. Confirm CI/CD secret configuration.

---

### Step 3: Create Helm Chart Files

Create standard Helm chart structure. **Important**: Claude Code uses `type: pod` agent (not `type: http` like Noah), requiring a full `PodTemplateSpec`.

#### Required Files:

- `chart/Chart.yaml` - Standard chart metadata
- `chart/templates/_helpers.tpl` - Standard Helm template helpers
- `chart/templates/secret.yaml` - Secret for Anthropic API key
- `chart/templates/pvc.yaml` - PersistentVolumeClaim for workspace
- `chart/templates/agent.yaml` - Agent CRD with pod specification

#### Key Configuration Points:

**A. Docker Image**

Image published by marketplace CI/CD to GHCR:

```yaml
image:
  repository: ghcr.io/mckinsey/agents-at-scale-marketplace/claude-code
  tag: "latest"  # Or use Chart.AppVersion
  pullPolicy: IfNotPresent
```

**B. Anthropic API Key**

Required for Claude Code to function. User provides during installation:

```bash
# Option 1: Direct key (chart creates secret)
ark install marketplace/claude-code --set anthropic.apiKey=$ANTHROPIC_API_KEY

# Option 2: Existing secret (user manages secret)
kubectl create secret generic anthropic-key --from-literal=api-key=$ANTHROPIC_API_KEY
ark install marketplace/claude-code --set anthropic.existingSecret=anthropic-key
```

Configuration in `values.yaml`:
```yaml
anthropic:
  apiKey: ""              # Set via --set or values file
  existingSecret: ""      # Reference to pre-created secret
```

**C. Agent Pod Template**

Agent CRD must include full `PodTemplateSpec` (not just HTTP endpoint). Key elements:

- Container runs `claude` command with `${ARK_USER_INPUT}`
- Mounts workspace PVC at `/workspace`
- Injects `ANTHROPIC_API_KEY` from secret
- Sets `restartPolicy: Never` for ephemeral execution

**Reference**: `ark/agents/claude.yaml` for complete template example.

**D. Result Filter**

Claude Code outputs JSON format `{"type":"result","result":"..."}`. JQ filter extracts the final result:

```yaml
resultFilter:
  jq: 'select(.type == "result") | .result'
```

**E. Persistent Storage**

Requires PersistentVolumeClaim with `ReadWriteMany` access mode. Support existing claims and configurable storage class:

```yaml
persistence:
  size: 10Gi
  accessMode: ReadWriteMany
  storageClass: ""        
  existingClaim: ""      
```

---

### Step 4: Update Marketplace Registry

Add entry to `marketplace.json`:

```json
{
  "agents": [
    {
      "name": "claude-code",
      "displayName": "Claude Code",
      "description": "AI-powered coding assistant by Anthropic",
      "category": "agent",
      "version": "0.1.0",
      "ark": {
        "type": "helm",
        "chartPath": "oci://ghcr.io/mckinsey/charts/claude-code"
      },
      "documentation": "https://github.com/mckinsey/agents-at-scale-marketplace/tree/main/agents/claude-code",
      "prerequisites": [
        "ARK Controller with pod agent support",
        "Anthropic API key"
      ]
    }
  ]
}
```

**Note**: Insert into the existing `agents` array, maintaining JSON format.

---

### Step 5: Validate Locally

```bash
cd agents/claude-code/chart

# Lint chart
helm lint .

# Test template rendering
helm template test . --debug --set anthropic.apiKey=test-key
```

---

## 4. CI/CD Workflow

**Automated by existing pipelines** (no changes needed):

- PR: Validates Dockerfile and Helm chart
- Merge to `main`: Release Please creates release PR
- Release merge: Builds and publishes Docker image + Helm chart to GHCR

---

## 5. Validation

Pre-commit validation:

```bash
cd agents-at-scale-marketplace

# Validate chart syntax
helm lint ./agents/claude-code/chart

# Test template rendering
helm template ./agents/claude-code/chart --debug
```

After release, end-users install via:
```bash
ark install marketplace/claude-code
```

---

## 6. Success Criteria

| Criterion | Validation |
|-----------|------------|
| Chart valid | `helm lint` passes |
| Agent CRD created | `kubectl get agent claude-code` |
| Secret created | `kubectl get secret` shows API key |
| Query execution works | Pod created, logs streamed, result extracted |
| CI/CD publishes | Image and chart available in GHCR |
