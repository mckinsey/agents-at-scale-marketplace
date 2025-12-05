# ARK Sandbox Tests

This directory contains tests for the ark-sandbox service.

## Running Tests

```bash
# From the service directory
cd services/ark-sandbox

# Run all tests
make test

# Or directly with pytest
PYTHONPATH=src uv run pytest tests/ -v
```

## Test Files

| File                  | Tests | Description                            |
| --------------------- | ----- | -------------------------------------- |
| `test_basic.py`       | 7     | Basic import and module tests          |
| `test_k8s_manager.py` | 7     | Kubernetes manager unit tests (mocked) |
| `test_mcp_tools.py`   | 5     | MCP tools tests (mocked)               |
| `test_templates.py`   | 25    | Argo WorkflowTemplate validation       |

## Test Categories

### Unit Tests (No cluster required)

Most tests use mocked Kubernetes clients, so they can run without a real cluster:

- Module imports
- K8s manager initialization
- MCP tool registration and execution

### Template Validation (No cluster required)

Tests validate Argo WorkflowTemplates:

- YAML syntax validity
- Required fields (apiVersion, kind, metadata.name, spec.templates)
- Template structure (inputs, outputs, resource actions)
- Naming conventions (ark-sandbox- prefix)
- Description annotations

### Integration Tests (Cluster required)

For full integration testing, deploy to a dev cluster:

```bash
# Deploy the service
devspace dev

# Apply CRDs
kubectl apply -f chart/crds/

# Apply WorkflowTemplates
kubectl apply -f templates/

# Create a test sandbox
kubectl apply -f - <<EOF
apiVersion: ark.mckinsey.com/v1alpha1
kind: Sandbox
metadata:
  name: test-sandbox
spec:
  image: python:3.12-slim
  ttlMinutes: 30
EOF

# Check sandbox status
kubectl get sandbox test-sandbox -o yaml
```
