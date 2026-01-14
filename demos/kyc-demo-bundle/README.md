# KYC Demo Bundle

Pre-configured KYC demo with specialized agents and multi-agent teams for customer onboarding.

## What's Included

### Agents
- **document-verifier** - Validates identity documents and performs fraud detection
- **risk-assessor** - Evaluates customer risk profile and regulatory compliance
- **compliance-reporter** - Synthesizes findings into audit-ready KYC reports

### Teams
- **kyc-verification-team** - Full onboarding workflow with document, risk, and compliance review
- **quick-screening-team** - Fast-track verification for low-risk customers

### Workflow Example
- **kyc-onboarding-workflow.yaml** - Complete KYC onboarding workflow example

## Prerequisites

### Required
- Kubernetes cluster (minikube, kind, or cloud provider)
- Ark controller installed (namespace: ark-system)
- kubectl CLI configured and authenticated
- helm CLI installed (v3.8+)
- A Model resource configured in Ark (e.g., `default` model in `default` namespace)

### Optional (for Argo Workflows)
- Argo Workflows installed (namespace: argo-workflows)
- Minio artifact storage configured
- ServiceAccount `argo-workflow` in `argo-workflows` namespace

## Installation

### Local Development (Minikube/Kind)

For local development with source code access:

```bash
# Clone marketplace repository
git clone https://github.com/mckinsey/agents-at-scale-marketplace
cd agents-at-scale-marketplace/demos/kyc-demo-bundle

# Install bundle only
make install

# Or install with Argo Workflows support
make install-with-argo

# Submit demo workflow
make demo

# Uninstall
make uninstall
```

#### Argo Workflows UI
Instead of using CLI, you may manually create a Workflow on the Argo Workflows UI (that can be accessed on http://localhost:2746/), and submit the content of `demos/kyc-demo-bundle/examples/kyc-onboarding-workflow.yaml` there to run it. The logs will display the results, and you may also view them on Ark Dashboard Queries section as well.

### Cloud Deployment

For cloud deployments where an Ark instance is already running.

**Step 1: Install Bundle**

```bash
ark install marketplace/demos/kyc-demo-bundle
```

This installs 3 agents and 2 teams in the default namespace. Argo Workflows RBAC is automatically configured to allow workflows to create and read Ark Queries.

**Step 2: Verify Installation**

```bash
# Check agents are available
kubectl get agents -n default

# Check teams are available
kubectl get teams -n default
```

**Step 3: Test Agents**

```bash
# Query individual agent
ark query document-verifier "Verify passport AB123456 for John Doe"

# Query team
ark query kyc-verification-team "Complete KYC for John Doe, US citizen"
```

## Argo Workflows Integration

To run automated KYC workflows using Argo:

**Step 1: Access Argo UI**

Inside of your cluster, access the Argo Workflows UI

**Step 2: Get Workflow YAML**

Go to the marketplace repository on GitHub:
```
https://github.com/mckinsey/agents-at-scale-marketplace/blob/main/demos/kyc-demo-bundle/examples/kyc-onboarding-workflow.yaml
```

Click **"Raw"** and copy the entire contents.

**Step 3: Submit Workflow**

1. In the Argo UI, click **"+ SUBMIT NEW WORKFLOW"**
2. Paste the copied YAML content
3. Click **"CREATE"**

**Step 4: Monitor Execution**

Watch the workflow execute in the UI. Results will appear in the logs and in the Ark Dashboard Queries section.

## Support

For issues or questions:
- [Ark Documentation](https://github.com/mckinsey/agents-at-scale)
- [Marketplace Repository](https://github.com/mckinsey/agents-at-scale-marketplace)

