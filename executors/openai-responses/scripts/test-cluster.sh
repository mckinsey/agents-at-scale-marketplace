#!/usr/bin/env bash
# Run a test query against the executor deployed on kind-ark-sandbox-test.
#
# Usage:
#   ./scripts/test-cluster.sh
#   ./scripts/test-cluster.sh --agent sql-generator-agent --input "Get top 10 orders"
#   ./scripts/test-cluster.sh --agent website-search-agent --input "ADAM GROOMING BN LTD"

set -euo pipefail

CONTEXT="${KUBECONTEXT:-kind-ark-sandbox-test}"
AGENT="${AGENT:-website-search-agent}"
INPUT="${INPUT:-ADAM GROOMING BN LTD}"

# Parse --agent and --input flags
while [[ $# -gt 0 ]]; do
  case "$1" in
    --agent) AGENT="$2"; shift 2 ;;
    --input) INPUT="$2"; shift 2 ;;
    *) echo "Unknown arg: $1" >&2; exit 1 ;;
  esac
done
QUERY_NAME="test-$(date +%s)"

cleanup() {
  kubectl --context "$CONTEXT" delete query "$QUERY_NAME" --ignore-not-found -n default > /dev/null 2>&1 || true
}
trap cleanup EXIT

echo "Creating query '$QUERY_NAME' → agent '$AGENT'"
echo "Input: $INPUT"
echo ""

kubectl --context "$CONTEXT" create -f - <<EOF
apiVersion: ark.mckinsey.com/v1alpha1
kind: Query
metadata:
  name: $QUERY_NAME
  namespace: default
spec:
  target:
    type: agent
    name: $AGENT
  input: "$INPUT"
EOF

echo "Waiting for result..."
for i in $(seq 1 30); do
  PHASE=$(kubectl --context "$CONTEXT" get query "$QUERY_NAME" -n default -o jsonpath='{.status.phase}' 2>/dev/null || echo "")
  if [[ "$PHASE" == "done" || "$PHASE" == "error" ]]; then
    break
  fi
  sleep 2
done

CONTENT=$(kubectl --context "$CONTEXT" get query "$QUERY_NAME" -n default -o jsonpath='{.status.response.content}')
PHASE=$(kubectl --context "$CONTEXT" get query "$QUERY_NAME" -n default -o jsonpath='{.status.phase}')

echo ""
echo "Phase  : $PHASE"
echo "Result : $CONTENT"
