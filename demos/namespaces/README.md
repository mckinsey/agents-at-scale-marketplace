# Demo Namespaces

Namespace manifests for ARK demo environments. Each file creates a Kubernetes namespace with labels and annotations used by the ARK landing page for demo discovery.

## How it works

The ARK landing page lists all namespaces with the label `ark.mckinsey.com/demo: "true"` and displays the name/description from annotations.

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