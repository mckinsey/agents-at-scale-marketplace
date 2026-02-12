#!/bin/bash
# ============================================================
# Sync Environment - Update Kubernetes from .env
# ============================================================
# Reads .env file and syncs all configurations to Kubernetes:
#   - Updates aigw-secret with API_TOKEN (from ARK or LX provider)
#   - Applies MCP server configs with envsubst
#   - Restarts deployments
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

# Export variables for envsubst (must be exported to be available in subshells)
export OPENAI_BASE_URL ANTHROPIC_BASE_URL PERPLEXITY_BASE_URL UBO_LLM_DEFAULT_PROVIDER UBO_LLM_DEFAULT_MODEL

# Update Kubernetes secret
echo "🔐 Updating aigw-secret..."
kubectl create secret generic aigw-secret \
  --from-literal=api-key="$API_TOKEN" \
  --from-literal=jwt-token="$API_TOKEN" \
  --from-literal=token="$API_TOKEN" \
  --dry-run=client -o yaml | kubectl apply -f -

echo "✅ Secret updated"
echo ""

# Apply MCP server configurations
echo "📦 Applying MCP server configurations..."

if [ -f mcp-servers/ubo-pdf-tools/k8s-direct.yaml ]; then
    echo "   → ubo-pdf-tools..."
    (cd mcp-servers/ubo-pdf-tools && envsubst < k8s-direct.yaml | kubectl apply -f -)
fi

if [ -f mcp-servers/ubo-web-tools/k8s-direct.yaml ]; then
    echo "   → ubo-web-tools..."
    (cd mcp-servers/ubo-web-tools && envsubst < k8s-direct.yaml | kubectl apply -f -) 2>/dev/null || true
fi

echo "✅ Configurations applied"
echo ""

# Restart deployments
echo "🔄 Restarting deployments..."
kubectl rollout restart deployment/ubo-pdf-tools 2>/dev/null && echo "   ✅ ubo-pdf-tools restarted" || true
kubectl rollout restart deployment/ubo-web-tools 2>/dev/null && echo "   ✅ ubo-web-tools restarted" || true

echo ""
echo "⏳ Waiting for rollouts to complete..."
kubectl rollout status deployment/ubo-pdf-tools -w --timeout=60s 2>/dev/null || true

echo ""
echo "════════════════════════════════════════════════════════════════════"
echo "✅ Sync Complete!"
echo "════════════════════════════════════════════════════════════════════"
echo ""
echo "All configurations are now synced with .env file."
echo ""
