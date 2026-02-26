#!/bin/bash
# ============================================================
# Sync Environment - Update Kubernetes from .env
# ============================================================
# Reads .env file and syncs all configurations to Kubernetes:
#   - Updates aigw-secret with API_TOKEN (from ARK or LX provider)
#   - Deploys/upgrades Helm release with credentials via --set flags
#   - Cleans up unmanaged resources
#
# SECURITY: Credentials are NEVER written to values.yaml
# They are passed to Helm via --set flags at deployment time
#
# Usage:
#   ./scripts/sync-env.sh
#
# Run this daily after updating API tokens in .env
# ============================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "════════════════════════════════════════════════════════════════════"
echo "🔄 Syncing Kubernetes with .env file"
echo "════════════════════════════════════════════════════════════════════"
echo ""

# Load .env
cd "$PROJECT_DIR"
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found"
    exit 1
fi

echo "📋 Loading .env..."
set -a  # Auto-export all variables
source .env
set +a

# Validate required variables
if [ -z "$API_TOKEN" ]; then
    echo "❌ Error: API_TOKEN not set in .env"
    echo "   Make sure API_TOKEN points to either ARK_DAILY_API_TOKEN or LX_DAILY_API_TOKEN"
    exit 1
fi

if [ -z "$AIGW_UUID" ]; then
    echo "❌ Error: AIGW_UUID not set in .env"
    echo "   Make sure AIGW_UUID points to either ARK_AIGW_UUID or LX_AIGW_UUID"
    exit 1
fi

echo "✅ Loaded environment variables:"
echo "   Provider: $([ "$API_TOKEN" = "$ARK_DAILY_API_TOKEN" ] && echo "ARK" || echo "LegacyX")"
echo "   AIGW_UUID: $AIGW_UUID"
echo "   OPENAI_BASE_URL: $OPENAI_BASE_URL"
echo "   ANTHROPIC_BASE_URL: $ANTHROPIC_BASE_URL"
echo "   PERPLEXITY_BASE_URL: $PERPLEXITY_BASE_URL"
echo "   UBO_LLM_DEFAULT_PROVIDER: $UBO_LLM_DEFAULT_PROVIDER"
echo "   UBO_LLM_DEFAULT_MODEL: $UBO_LLM_DEFAULT_MODEL"
echo "   API_TOKEN: ${API_TOKEN:0:20}..."
echo ""

# Export environment variables for Kubernetes config maps
export OPENAI_BASE_URL ANTHROPIC_BASE_URL PERPLEXITY_BASE_URL UBO_LLM_DEFAULT_PROVIDER UBO_LLM_DEFAULT_MODEL

# Update Kubernetes secrets and models
echo "🔐 Updating secrets and models..."

# Update aigw-secret (used by MCP servers)
echo "   → aigw-secret..."
kubectl create secret generic aigw-secret \
  --from-literal=api-key="$API_TOKEN" \
  --from-literal=jwt-token="$API_TOKEN" \
  --from-literal=token="$API_TOKEN" \
  --dry-run=client -o yaml | kubectl apply -f -

# Smart cleanup: only delete if token changed or not managed by Helm
echo "   → Checking existing resources..."

# Function to check if resource is managed by our Helm release
is_managed_by_our_helm() {
    local RESOURCE_TYPE=$1
    local RESOURCE_NAME=$2
    
    MANAGED_BY=$(kubectl get "$RESOURCE_TYPE" "$RESOURCE_NAME" -n default -o jsonpath='{.metadata.labels.app\.kubernetes\.io/managed-by}' 2>/dev/null)
    RELEASE_NAME=$(kubectl get "$RESOURCE_TYPE" "$RESOURCE_NAME" -n default -o jsonpath='{.metadata.annotations.meta\.helm\.sh/release-name}' 2>/dev/null)
    
    if [ "$MANAGED_BY" = "Helm" ] && [ "$RELEASE_NAME" = "kyc-onboarding-bundle" ]; then
        return 0  # True - managed by our Helm release
    else
        return 1  # False - not managed by our Helm release
    fi
}

# Check secrets
if kubectl get secret ai-gateway-azure-openai -n default &>/dev/null; then
    if ! is_managed_by_our_helm secret ai-gateway-azure-openai; then
        echo "      • Secret not managed by our Helm release, deleting for adoption..."
        kubectl delete secret ai-gateway-azure-openai -n default
    else
        # Managed by Helm - check if token changed
        EXISTING_TOKEN=$(kubectl get secret ai-gateway-azure-openai -n default -o jsonpath='{.data.token}' 2>/dev/null | base64 -d)
        
        if [ "$EXISTING_TOKEN" != "$API_TOKEN" ]; then
            echo "      • Token changed, updating via Helm..."
        else
            echo "      • Token unchanged, skipping deletion"
        fi
    fi
fi

# Check models
if kubectl get model default -n default &>/dev/null; then
    if ! is_managed_by_our_helm model default; then
        echo "      • Model not managed by our Helm release, deleting for adoption..."
        kubectl delete model default -n default
    fi
fi

# Check agents (delete all not managed by our Helm release)
UNMANAGED_AGENTS=$(kubectl get agents -n default -o json 2>/dev/null | \
    jq -r '.items[] | select((.metadata.labels."app.kubernetes.io/managed-by" != "Helm") or (.metadata.annotations."meta.helm.sh/release-name" != "kyc-onboarding-bundle")) | .metadata.name' 2>/dev/null)

if [ -n "$UNMANAGED_AGENTS" ]; then
    echo "      • Found agents not managed by our Helm release:"
    for agent in $UNMANAGED_AGENTS; do
        echo "        - Deleting: $agent"
        kubectl delete agent "$agent" -n default --ignore-not-found=true
    done
fi

# Check teams (delete all not managed by our Helm release)
UNMANAGED_TEAMS=$(kubectl get teams -n default -o json 2>/dev/null | \
    jq -r '.items[] | select((.metadata.labels."app.kubernetes.io/managed-by" != "Helm") or (.metadata.annotations."meta.helm.sh/release-name" != "kyc-onboarding-bundle")) | .metadata.name' 2>/dev/null)

if [ -n "$UNMANAGED_TEAMS" ]; then
    echo "      • Found teams not managed by our Helm release:"
    for team in $UNMANAGED_TEAMS; do
        echo "        - Deleting: $team"
        kubectl delete team "$team" -n default --ignore-not-found=true
    done
fi

# Upgrade Helm release (creates/updates Secret + Model resources)
echo "   → Running Helm upgrade..."

# Test webhook connectivity first
echo "      • Testing ARK webhook service..."
if ! kubectl run test-webhook-$$ --image=curlimages/curl --rm -i --restart=Never -- \
  curl -sk -m 5 https://ark-webhook-service.ark-system.svc:443 &>/dev/null; then
  echo "      ⚠️  ARK webhook not responding, temporarily disabling webhooks..."
  kubectl delete validatingwebhookconfiguration ark-validating-webhook-configuration --ignore-not-found=true
  kubectl delete mutatingwebhookconfiguration ark-mutating-webhook-configuration --ignore-not-found=true
  echo "      • Webhook configurations removed (ARK controller will recreate them)"
else
  echo "      ✅ ARK webhook service responding"
fi

helm upgrade --install kyc-onboarding-bundle "$PROJECT_DIR/chart" \
  --namespace default \
  --set aigw.token="$API_TOKEN" \
  --set aigw.uuid="$AIGW_UUID" \
  --wait \
  --timeout 5m

if [ $? -eq 0 ]; then
    echo "   ✅ Helm upgrade completed"
else
    echo "   ❌ Helm upgrade failed"
    exit 1
fi

echo "✅ Secrets and models updated"
echo ""

# Refresh ARK resources to pick up new secrets
echo ""
echo "🔄 Refreshing ARK resources (models, agents, teams)..."

# Force reconciliation by adding/updating annotation
echo "   → Annotating resources with secret-updated timestamp..."
TIMESTAMP=$(date +%s)
kubectl annotate model --all -n default secret-updated="$TIMESTAMP" --overwrite 2>/dev/null || echo "   ℹ️  No models found"
kubectl annotate agent --all -n default secret-updated="$TIMESTAMP" --overwrite 2>/dev/null || echo "   ℹ️  No agents found"
kubectl annotate team --all -n default secret-updated="$TIMESTAMP" --overwrite 2>/dev/null || echo "   ℹ️  No teams found"

# Wait for models to become available
echo ""
echo "⏳ Waiting for models to become available (timeout: 60s)..."
WAIT_START=$(date +%s)
while true; do
    AVAILABLE_COUNT=$(kubectl get models -n default -o json 2>/dev/null | \
      jq '[.items[] | select(.status.conditions[]? | select(.type=="ModelAvailable" and .status=="True"))] | length' 2>/dev/null || echo "0")
    TOTAL_COUNT=$(kubectl get models -n default -o json 2>/dev/null | jq '.items | length' 2>/dev/null || echo "0")
    
    if [ "$TOTAL_COUNT" -eq 0 ]; then
        echo "   ℹ️  No models found to check"
        break
    fi
    
    if [ "$AVAILABLE_COUNT" -eq "$TOTAL_COUNT" ]; then
        echo "   ✅ All $TOTAL_COUNT model(s) are available"
        break
    fi
    
    ELAPSED=$(($(date +%s) - WAIT_START))
    if [ $ELAPSED -gt 60 ]; then
        echo "   ⚠️  Timeout: $AVAILABLE_COUNT/$TOTAL_COUNT model(s) available after 60s"
        echo "   💡 Run 'kubectl get models -n default' to check status"
        break
    fi
    
    echo "   ⏳ Waiting for models: $AVAILABLE_COUNT/$TOTAL_COUNT available..."
    sleep 3
done

# Show final status
echo ""
echo "📊 Current Resource Status:"
kubectl get models,agents,teams -n default 2>/dev/null | grep -v "No resources" || echo "   No resources found"

echo ""
echo "════════════════════════════════════════════════════════════════════"
echo "✅ Sync Complete!"
echo "════════════════════════════════════════════════════════════════════"
echo ""
echo "Updated:"
echo "  • Secrets: aigw-secret, ai-gateway-azure-openai (+ any other model secrets)"
echo "  • Resources: models, agents, teams (annotated for reconciliation)"
echo ""
echo "If models/agents/teams still show unavailable, wait 30-60 seconds for ARK"
echo "controller to reconcile, or check status with:"
echo "  kubectl get models,agents,teams -n default"
echo ""
