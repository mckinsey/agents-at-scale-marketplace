# ARK Marketplace Common Library Chart

Reusable Helm library chart providing common templates for ARK Marketplace items.

## Purpose

This library chart solves the **external OCI chart label problem**: When marketplace services use external OCI charts as dependencies (charts not maintained by us), those charts often don't support custom labels. This prevents the ARK dashboard from detecting installations.

This library provides a **post-install hook** that automatically patches deployments with the required `ark.mckinsey.com/marketplace-item` label after installation.

## When to Use

Use this library chart if your marketplace service:

✅ **Wraps an external OCI chart** (e.g., Phoenix wraps `oci://registry-1.docker.io/arizephoenix/phoenix-helm`)
✅ **External chart ignores `global.labels`** in values.yaml
✅ **Creates Deployments** (not just StatefulSets or DaemonSets)

**Don't use** if your service:
- Has full control over chart templates (just add labels directly to templates)
- Only creates CRD resources (ARK detects those automatically)
- Doesn't create any Deployments

## How to Use

### 1. Add Dependency

Add this library chart as a dependency in your service's `Chart.yaml`:

```yaml
# services/your-service/chart/Chart.yaml
apiVersion: v2
name: your-service
version: 1.0.0
dependencies:
  - name: ark-marketplace-common
    version: "0.1.x"
    repository: "file://../../charts/ark-marketplace-common"
  - name: external-chart
    version: "1.0.0"
    repository: "oci://registry.example.com/charts"
```

### 2. Add Required Labels

Ensure your `values.yaml` contains the marketplace label:

```yaml
# services/your-service/chart/values.yaml
global:
  labels:
    ark.mckinsey.com/marketplace-item: "your-service"  # Must match marketplace.json name
```

### 3. Include Post-Install Hook

Create a template file that includes the hook:

```yaml
# services/your-service/chart/templates/marketplace-label-patch.yaml
{{- include "ark-marketplace.labelPatchHook" (dict "Chart" .Chart "Release" .Release "Values" .Values) }}
```

### 4. Update Dependencies

Build the chart dependencies:

```bash
cd services/your-service/chart
helm dependency update
```

## What It Does

When you install your service, the library chart:

1. **Pre-install**: Creates ServiceAccount, Role, and RoleBinding with deployment patch permissions
2. **Post-install**: Launches a Job that:
   - Waits for deployment(s) to be created
   - Patches ALL deployments in the namespace with `ark.mckinsey.com/marketplace-item` label
   - Waits for deployments to become available
3. **Cleanup**: Automatically deletes the Job after successful completion

## Complete Example

See `services/phoenix/` for a complete working example.

### Chart.yaml
```yaml
apiVersion: v2
name: phoenix
version: 1.0.0
dependencies:
  - name: ark-marketplace-common
    version: "0.1.0"
    repository: "file://../../charts/ark-marketplace-common"
  - name: phoenix-helm
    version: "4.2.0"
    repository: "oci://registry-1.docker.io/arizephoenix"
```

### values.yaml
```yaml
global:
  labels:
    ark.mckinsey.com/marketplace-item: "phoenix"
```

### templates/marketplace-label-patch.yaml
```yaml
{{- include "ark-marketplace.labelPatchHook" (dict "Chart" .Chart "Release" .Release "Values" .Values) }}
```

## Testing

After installation, verify the label was applied:

```bash
# Install your service
helm upgrade --install your-service ./chart -n your-namespace

# Verify label on deployment
kubectl get deployment -n your-namespace \
  -l ark.mckinsey.com/marketplace-item=your-service \
  -o jsonpath='{.items[0].metadata.labels.ark\.mckinsey\.com/marketplace-item}'

# Expected output: your-service
```

## How It Works

### Timeline

```
t0: helm install starts
t1: Pre-install hook creates RBAC resources (ServiceAccount, Role, RoleBinding)
t2: External chart creates Deployment (without marketplace label)
t3: Post-install hook Job starts
t4: Job waits for deployment to exist
t5: Job patches deployment with label
t6: Job waits for deployment to be Available
t7: Job completes, gets deleted
```

### Race Condition Handling

The hook includes wait logic to handle the race condition where the deployment might not exist yet when the post-install hook runs:

- **Wait for deployment creation**: Retries for up to 60 seconds
- **Wait for deployment availability**: Uses `kubectl wait --for=condition=available`
- **Backoff and retry**: Job has `backoffLimit: 3` for automatic retries

## Troubleshooting

### Label not applied after installation

1. **Check if Job ran successfully**:
   ```bash
   kubectl get jobs -n your-namespace
   kubectl logs -n your-namespace job/your-service-label-patcher
   ```

2. **Check RBAC permissions**:
   ```bash
   kubectl get role,rolebinding -n your-namespace | grep label-patcher
   ```

3. **Verify values.yaml has label**:
   ```bash
   yq eval '.global.labels."ark.mckinsey.com/marketplace-item"' chart/values.yaml
   ```

### Job fails with "No deployments found"

This means the external chart didn't create any Deployments. Check:
- Does the chart create StatefulSets or DaemonSets instead?
- Is the chart configured correctly?
- Are there any chart installation errors?

### Dashboard still shows "not installed"

1. **Verify label on deployment**:
   ```bash
   kubectl get deployment -n your-namespace -o yaml | grep ark.mckinsey.com/marketplace-item
   ```

2. **Check label value matches marketplace.json name**:
   - Label value: `ark.mckinsey.com/marketplace-item: "phoenix"`
   - marketplace.json: `"name": "phoenix"`
   - These MUST match exactly

3. **Verify ark-api has labelSelector support** (requires ark v0.2.0+):
   ```bash
   kubectl port-forward -n ark-system svc/ark-api 8080:8080
   curl "http://localhost:8080/v1/resources/apis/apps/v1/Deployment?namespace=your-namespace&labelSelector=ark.mckinsey.com%2Fmarketplace-item%3Dyour-service"
   ```

## Alternative Solutions

If you can't use this library chart, consider:

1. **Fork the external chart**: Modify templates to support `global.labels`
2. **Manual patching**: Document manual `kubectl patch` command for users
3. **Helm post-renderer**: Use `--post-renderer` with kustomize (requires changes to installation commands)

## Maintenance

This library chart is maintained alongside the marketplace repo. When updating:

1. Update version in `Chart.yaml`
2. Test with all services using the library
3. Update this README if behavior changes

## References

- [Helm Library Charts](https://helm.sh/docs/topics/library_charts/)
- [Helm Hooks](https://helm.sh/docs/topics/charts_hooks/)
