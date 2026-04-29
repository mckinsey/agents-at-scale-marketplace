#!/bin/bash
set -euo pipefail

WF_NAME="${1:-}"
NAMESPACE="${2:-default}"

if [ -z "$WF_NAME" ]; then
    WF_NAME=$(kubectl -n "$NAMESPACE" get wf -o json 2>/dev/null \
      | python3 -c "
import sys, json
data = json.load(sys.stdin)
items = [w for w in data.get('items', [])
         if w.get('spec', {}).get('workflowTemplateRef', {}).get('name') == 'onboarding-generate']
items.sort(key=lambda w: w['metadata'].get('creationTimestamp',''), reverse=True)
print(items[0]['metadata']['name'] if items else '')
")
    if [ -z "$WF_NAME" ]; then
        echo "ERROR: no Workflow found with workflowTemplateRef=onboarding-generate."
        echo "       Pass the workflow name explicitly: $0 <workflow-name>"
        exit 1
    fi
    echo "Using latest workflow: $WF_NAME"
fi

REMOTE_DIR="output/${WF_NAME}"
LOCAL_DIR="./output/${WF_NAME}"
REMOTE_FILES=("analysis.md" "ONBOARDING.md" "TICKET.md")

mkdir -p "$LOCAL_DIR"

echo "=== port-forwarding file-gateway-api ==="
kubectl -n "$NAMESPACE" port-forward svc/file-gateway-api 18080:80 >/dev/null 2>&1 &
PF_PID=$!
trap 'kill $PF_PID 2>/dev/null || true' EXIT
sleep 2

ANY_OK=0
for NAME in "${REMOTE_FILES[@]}"; do
    LOCAL_PATH="$LOCAL_DIR/$NAME"
    REMOTE_KEY="$REMOTE_DIR/$NAME"
    HTTP=$(curl -sS -o "$LOCAL_PATH" -w "%{http_code}" \
        "http://localhost:18080/files/$REMOTE_KEY/download" || echo "000")
    if [ "$HTTP" = "200" ]; then
        SIZE=$(wc -c < "$LOCAL_PATH" | tr -d ' ')
        echo "  ✓ $REMOTE_KEY -> $LOCAL_PATH  ($SIZE bytes)"
        ANY_OK=1
    else
        echo "  ✗ $REMOTE_KEY (HTTP $HTTP)"
        rm -f "$LOCAL_PATH"
    fi
done

if [ "$ANY_OK" = "0" ]; then
    echo ""
    echo "ERROR: no files downloaded from $REMOTE_DIR."
    echo "       Check that the workflow '$WF_NAME' finished:"
    echo "         kubectl -n $NAMESPACE get wf $WF_NAME"
    exit 1
fi

echo ""
echo "Open the generated files:"
for NAME in "${REMOTE_FILES[@]}"; do
    LOCAL_PATH="$LOCAL_DIR/$NAME"
    [ -f "$LOCAL_PATH" ] && echo "  open \"$LOCAL_PATH\""
done
