# KYC Demo Bundle

KYC customer onboarding demo with file-based multi-agent workflows.

## What's Included

- **5 agents**: document-verifier, ubo-extractor, sanctions-screener, risk-assessor, compliance-reporter
- **4 teams**: identity-verification-team, ownership-analysis-team, compliance-screening-team, risk-assessment-team
- **file-gateway**: S3-compatible storage with filesystem MCP
- **Argo workflow**: 5-step automated KYC onboarding pipeline with UBO tree generation, sanctions/PEP screening, and risk assessment

Agents read customer data from plain text files and write reports using MCP filesystem tools.

## Prerequisites

- Kubernetes cluster (minikube, kind, or cloud)
- Ark controller installed
- Argo Workflows installed
- kubectl and helm CLI

## Local Development

```bash
# 3 simple steps:
cd agents-at-scale-marketplace/demos/kyc-demo-bundle

make install-with-argo      # 1. Install everything
make upload-data            # 2. Upload example customer file
make kyc-demo               # 3. Run KYC workflow

# View results
kubectl get workflows -n default
# Access ARK Dashboard → Workflow Templates (template is visible)
# Access ARK Dashboard → Files section (download report)

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

