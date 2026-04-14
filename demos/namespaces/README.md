# Demo Namespaces

Namespace manifests for Ark demo environments. Each file creates a Kubernetes namespace with labels and annotations used by the Ark landing page for demo discovery.

## How it works

The Ark landing page lists all namespaces with the label `ark.mckinsey.com/demo: "true"` and displays the name/description from annotations.

## Usage

```bash
kubectl apply -f cobol-demo.yaml
kubectl apply -f kyc-demo.yaml
```

## Adding a new demo namespace

Create a YAML file following this pattern:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: my-demo
  labels:
    ark.mckinsey.com/demo: "true"
  annotations:
    ark.mckinsey.com/demo-name: "My Demo"
    ark.mckinsey.com/demo-description: "Short description of the demo"
```