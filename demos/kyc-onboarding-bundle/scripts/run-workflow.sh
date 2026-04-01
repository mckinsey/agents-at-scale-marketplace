#!/bin/bash
# ============================================================
# Run Workflow - Convenient workflow launcher
# ============================================================
# Launches Argo workflows using shortened names.
#
# Usage:
#   ./scripts/run-workflow.sh <short-name> [execution-mode]
#
# Examples:
#   ./scripts/run-workflow.sh vessels fake
#   ./scripts/run-workflow.sh ownership seq
#   ./scripts/run-workflow.sh controllers parallel
#
# Execution modes:
#   - fake: Use fake data (fast testing)
#   - seq: Sequential extraction (slower, more reliable, default)
#   - parallel: Parallel extraction (faster)
# ============================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Resolve workflow name from short name
resolve_workflow() {
    case "$1" in
        # Phase 0 - Profile Setup
        init|profile-init|pi)
            echo "lx-profile-initialization"
            ;;
        requirements|req|rs)
            echo "lx-requirements-and-standards"
            ;;
        
        # Phase I - Customer Due Diligence
        ownership|os)
            echo "lx-retrieve-ownership-structure"
            ;;
        controllers|kc)
            echo "lx-retrieve-key-controllers"
            ;;
        vessels|entities|ev)
            echo "lx-retrieve-entities-vessels"
            ;;
        purpose|por)
            echo "lx-assess-purpose-of-relationship"
            ;;
        
        # Phase II - Profile Enrichment
        enrichment|enrich|pe)
            echo "lx-profile-enrichment"
            ;;
        
        # Phase III - Risk Screening
        adverse|media|ams)
            echo "lx-adverse-media-screening"
            ;;
        sanctions|blacklist|bss)
            echo "lx-blacklist-sanction-screening"
            ;;
        
        # Phase IV - Risk Assessment & Reporting
        risk|assessment|ira)
            echo "lx-initial-risk-assessment"
            ;;
        memo|kyc-memo|km)
            echo "lx-kyc-memo"
            ;;
        finalization|final|pf)
            echo "lx-profile-finalization"
            ;;
        
        *)
            echo ""
            ;;
    esac
}

# Display usage
show_usage() {
    echo "════════════════════════════════════════════════════════════════════"
    echo "🚀 KYC Workflow Launcher"
    echo "════════════════════════════════════════════════════════════════════"
    echo ""
    echo "Usage: $0 <short-name> [execution-mode]"
    echo ""
    echo "Available workflows (KYC process phases):"
    echo ""
    echo "  Phase 0 - Profile Setup:"
    echo "    init, pi          → lx-profile-initialization"
    echo "    requirements, req → lx-requirements-and-standards"
    echo ""
    echo "  Phase I - Customer Due Diligence:"
    echo "    ownership, os     → lx-retrieve-ownership-structure"
    echo "    controllers, kc   → lx-retrieve-key-controllers"
    echo "    vessels, entities → lx-retrieve-entities-vessels"
    echo "    purpose, por      → lx-assess-purpose-of-relationship"
    echo ""
    echo "  Phase II - Profile Enrichment:"
    echo "    enrichment, pe    → lx-profile-enrichment"
    echo ""
    echo "  Phase III - Risk Screening:"
    echo "    adverse, media    → lx-adverse-media-screening"
    echo "    sanctions, bss    → lx-blacklist-sanction-screening"
    echo ""
    echo "  Phase IV - Risk Assessment & Reporting:"
    echo "    risk, assessment  → lx-initial-risk-assessment"
    echo "    memo, kyc-memo    → lx-kyc-memo"
    echo "    finalization, pf  → lx-profile-finalization"
    echo ""
    echo "Execution modes (optional, default: sequential):"
    echo "    fake              → Use fake data (fast testing, ~3 min)"
    echo "    seq               → Sequential extraction (reliable, ~30 min)"
    echo "    parallel          → Parallel extraction (faster, ~20 min)"
    echo ""
    echo "Examples:"
    echo "    $0 vessels fake           # Quick test with fake data"
    echo "    $0 ownership seq          # Full sequential run"
    echo "    $0 adverse parallel       # Parallel screening"
    echo "    $0 risk                   # Use default mode (sequential)"
    echo ""
    exit 1
}

# Check arguments
if [ $# -lt 1 ]; then
    show_usage
fi

SHORT_NAME="$1"
EXEC_MODE="${2:-sequential}"

# Resolve workflow name
WORKFLOW_NAME=$(resolve_workflow "$SHORT_NAME")

if [ -z "$WORKFLOW_NAME" ]; then
    echo "❌ Error: Unknown workflow short-name: '$SHORT_NAME'"
    echo ""
    show_usage
fi

# Validate execution mode and translate to full name
case "$EXEC_MODE" in
    fake)
        FULL_EXEC_MODE="fake"
        ;;
    seq)
        FULL_EXEC_MODE="sequential"
        ;;
    parallel)
        FULL_EXEC_MODE="parallel"
        ;;
    *)
        echo "❌ Error: Invalid execution mode: '$EXEC_MODE'"
        echo "   Valid modes: fake, seq, parallel"
        exit 1
        ;;
esac

echo "════════════════════════════════════════════════════════════════════"
echo "🚀 Launching Workflow"
echo "════════════════════════════════════════════════════════════════════"
echo ""
echo "Short name:       $SHORT_NAME"
echo "Workflow:         $WORKFLOW_NAME"
echo "Execution mode:   $EXEC_MODE → $FULL_EXEC_MODE"
echo ""

# Create workflow
WORKFLOW_YAML=$(cat <<EOF
apiVersion: argoproj.io/v1alpha1
kind: Workflow
metadata:
  generateName: ${WORKFLOW_NAME}-${EXEC_MODE}-
spec:
  workflowTemplateRef:
    name: ${WORKFLOW_NAME}
  arguments:
    parameters:
      - name: execution-mode
        value: "${FULL_EXEC_MODE}"
EOF
)

echo "Creating workflow..."
WORKFLOW_ID=$(echo "$WORKFLOW_YAML" | kubectl create -f - -o jsonpath='{.metadata.name}')

if [ -z "$WORKFLOW_ID" ]; then
    echo "❌ Failed to create workflow"
    exit 1
fi

echo ""
echo "════════════════════════════════════════════════════════════════════"
echo "✅ Workflow Created"
echo "════════════════════════════════════════════════════════════════════"
echo ""
echo "Workflow ID: $WORKFLOW_ID"
echo ""
echo "Monitor with:"
echo "  kubectl get workflow $WORKFLOW_ID -w"
echo ""
echo "View logs:"
echo "  kubectl logs -l workflows.argoproj.io/workflow=$WORKFLOW_ID -f"
echo ""
echo "Get status:"
echo "  kubectl get workflow $WORKFLOW_ID -o json | jq '{phase: .status.phase, progress: .status.progress, message: .status.message}'"
echo ""
