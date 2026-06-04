# LiteLLM

Central LLM credential broker for Ark. Runs in the **system namespace**
(`ark-system`) and holds every provider API key. Tenants reach models through
its OpenAI-compatible `/v1` endpoint and never see provider secrets.

Wraps the official [`litellm-helm`](https://github.com/BerriAI/litellm/tree/main/deploy/charts/litellm-helm)
chart. This wrapper adds Ark annotations, a master-key Secret, and a
NetworkPolicy. Postgres ships as a bundled subchart, enabling per-tenant virtual
keys, spend tracking, and runtime model management.

## Two parts, one service

- **Data plane** — the LiteLLM proxy + Postgres (via the `litellm-helm` subchart).
- **Control plane** — a bundled **model provider** (`modelProvider.*`) that syncs
  Ark `Model` resources and scoped virtual keys into tenant namespaces. Enabled
  by default; set `modelProvider.enabled=false` for a proxy-only deployment.

The provider's source (`src/`) and image (`Dockerfile`) live in this directory.

## Prerequisites

Create the provider-key Secret (only the keys you use):

```bash
kubectl create secret generic litellm-provider-secrets -n ark-system \
  --from-literal=OPENAI_API_KEY=sk-... \
  --from-literal=ANTHROPIC_API_KEY=sk-ant-... \
  --from-literal=AZURE_API_BASE=https://....openai.azure.com \
  --from-literal=AZURE_API_KEY=... \
  --from-literal=AZURE_API_VERSION=2024-02-01
```

## Install

**DevSpace (local dev):**
```bash
cd services/litellm
devspace deploy
```

**Helm:**
```bash
cd services/litellm
helm dependency update chart/
helm install litellm ./chart -n ark-system --create-namespace
# production: add --set masterKey=sk-... and override the admin/admin UI login
```

Enable the models you need in `chart/values.yaml` under
`litellm-helm.proxy_config.model_list` (OpenAI / Azure / Anthropic / Bedrock
examples included), ensuring the matching env vars exist in the Secret above.

## Verify

```bash
kubectl port-forward -n ark-system svc/litellm 4000:4000
export MASTER_KEY=sk-your-master-key

# List configured models
curl http://localhost:4000/v1/models -H "Authorization: Bearer $MASTER_KEY"

# Mint a per-tenant virtual key scoped to specific models
curl -X POST http://localhost:4000/key/generate \
  -H "Authorization: Bearer $MASTER_KEY" -H "Content-Type: application/json" \
  -d '{"models": ["gpt-4o"], "metadata": {"team": "tenant-a"}}'

# Chat completion through the proxy
curl http://localhost:4000/v1/chat/completions \
  -H "Authorization: Bearer $MASTER_KEY" -H "Content-Type: application/json" \
  -d '{"model": "gpt-4o", "messages": [{"role": "user", "content": "ping"}]}'
```

## Admin UI

LiteLLM serves a dashboard at `/ui` on the proxy port (login with the master
key). Expose it via Gateway API:

```bash
helm install litellm ./chart -n ark-system \
  --set httpRoute.enabled=true   # UI at http://litellm.ark-system.127.0.0.1.nip.io:8080/ui
```

To surface it as a tile in the Ark dashboard, set the marketplace UI annotations
on the proxy service:

```bash
--set litellm-helm.service.annotations.ark\.mckinsey\.com/marketplace-item-ui-url=https://litellm.example.com/ui \
--set litellm-helm.service.annotations.ark\.mckinsey\.com/marketplace-item-ui-label="LiteLLM"
```

## Model provider (control plane)

Reconciles `Model` resources + scoped virtual keys into tenant namespaces, so
tenants reference models by name and hold only a scoped token — never a provider
key. Every `reconcileIntervalSeconds`, for each target namespace it lists models
from LiteLLM, ensures a `litellm-vkey` Secret (minting a scoped key if absent),
upserts one `Model` per allowed model, and prunes the rest. Only resources
labelled `app.kubernetes.io/managed-by: litellm-model-provider` are touched.

Targets are provider config:
```yaml
modelProvider:
  targets:
    - namespace: tenant-a          # all models (unrestricted key)
    - namespace: tenant-b
      models: [gpt-4o]             # scoped subset
```

### Key scope

The per-tenant key (`litellm-vkey`, alias `ark-<namespace>`) is a **virtual key,
not the master key** — it can call `/v1/*` but not admin endpoints, holds no
provider secrets, and is centrally revocable.

A target with **no `models` list gets an unrestricted key** (`models: []` = access
to every model the proxy exposes). This is intentional: tenants still hold only a
scoped, revocable token and never see provider credentials. To restrict a tenant
to a subset, set its `models`:

```yaml
modelProvider:
  targets:
    - namespace: tenant-a            # all models (unrestricted key)
    - namespace: tenant-b
      models: [gpt-4o]               # key + Model CRs limited to gpt-4o
```

It runs with a **ClusterRole** (manages Models + the vkey Secret across
namespaces) — a privileged control-plane component, hence system-namespace only.
It is a first cut of a reusable model-provider pattern (`provider` loop +
swappable `backend`). Verify:

```bash
kubectl get models -n tenant-a
kubectl logs -n ark-system deploy/litellm-model-provider -f
```

### Lifecycle & cleanup

While the provider runs, it reconciles to LiteLLM: **remove a model from LiteLLM**
(config or the dashboard's `/model/delete`) and the matching `Model` resources are
**pruned** from tenant namespaces on the next reconcile.

Generated resources are **not** garbage-collected when the provider is uninstalled
— a tenant `Model` can't own-ref the provider (it lives in another namespace, which
Kubernetes GC forbids). After uninstalling, clean up by label (covers both the
Models and the `litellm-vkey` secrets):

```bash
kubectl delete models  -A -l app.kubernetes.io/managed-by=litellm-model-provider
kubectl delete secrets -A -l app.kubernetes.io/managed-by=litellm-model-provider
```

## Network access

The NetworkPolicy allows ingress to port 4000 only from `ark-system` and
namespaces labelled `ark.mckinsey.com/litellm-access: "true"`:

```bash
kubectl label namespace tenant-a ark.mckinsey.com/litellm-access=true
```

## Configuration

| Value | Default | Purpose |
|-------|---------|---------|
| `masterKey` | `sk-1234` | Master key (weak dev default — change for prod); creates the master-key Secret. |
| `litellm-helm.envVars.UI_USERNAME/UI_PASSWORD` | `admin`/`admin` | Dashboard login (weak dev default — change for prod). |
| `networkPolicy.enabled` | `true` | Restrict ingress to port 4000. |
| `networkPolicy.accessLabel` | `ark.mckinsey.com/litellm-access` | Namespace label granting access. |
| `litellm-helm.proxy_config.model_list` | one example | Models exposed by the proxy. |
| `litellm-helm.db.deployStandalone` | `true` | Bundle Postgres. Set `false` + `db.useExisting` for an external DB. |

See the [upstream chart values](https://github.com/BerriAI/litellm/blob/main/deploy/charts/litellm-helm/values.yaml)
for everything passed under `litellm-helm`.
