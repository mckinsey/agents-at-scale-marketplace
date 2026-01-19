# KYC Demo Bundle

KYC customer onboarding demo with file-based multi-agent workflows.

## What's Included

- **3 agents**: document-verifier, risk-assessor, compliance-reporter
- **2 teams**: kyc-verification-team, quick-screening-team
- **file-gateway**: S3-compatible storage with filesystem MCP
- **Argo workflow**: Automated KYC onboarding pipeline

Agents read customer data from plain text files and write reports using MCP filesystem tools.

## Prerequisites

- Kubernetes cluster (minikube, kind, or cloud)
- Ark controller installed
- Argo Workflows installed
- kubectl and helm CLI

## Local Development

```bash
# Clone and install
git clone https://github.com/mckinsey/agents-at-scale-marketplace
cd agents-at-scale-marketplace/demos/kyc-demo-bundle

make install-with-argo  # Install bundle
make upload-data        # Upload example customer file
make demo               # Submit workflow

# View results
kubectl get workflows -n default
# Access Ark Dashboard → Files section to download report

# Cleanup
make uninstall
```

## Cloud Deployment

```bash
# Install
ark install marketplace/demos/kyc-demo-bundle

# Upload customer data via Dashboard
# 1. Go to Ark Dashboard → Files section
# 2. Create folder: reports/
# 3. Upload john-doe.txt to customers/

# Submit workflow via Argo UI
# Get workflow YAML from:
# https://github.com/mckinsey/agents-at-scale-marketplace/blob/main/demos/kyc-demo-bundle/examples/kyc-onboarding-workflow.yaml
```

See `examples/data/customers/john-doe.txt` for customer data format.

