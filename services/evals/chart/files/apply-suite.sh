#!/usr/bin/env bash
# Materialize a suite folder into a ConfigMap (story 01).
#
# A suite is a readable folder on disk:
#
#   <suite>/suite.json
#   <suite>/dataset.json
#   <suite>/judges/quality.prompt.txt
#   <suite>/judges/quality.schema.json
#
# ConfigMap keys cannot contain '/', so the judges/ files are flattened to
# dotted keys (judges.quality.prompt.txt). When the ConfigMap is mounted as a
# volume, each key becomes a file in the mount dir, which is exactly what the
# engine's suite loader reads.
#
# Usage:  ./apply-suite.sh <suite-dir> [namespace]
# Example: ./apply-suite.sh kyc-profile-init default
set -euo pipefail

SUITE_DIR="${1:?usage: apply-suite.sh <suite-dir> [namespace]}"
NAMESPACE="${2:-default}"

if [[ ! -f "$SUITE_DIR/suite.json" ]]; then
  echo "ERROR: $SUITE_DIR/suite.json not found — is this a suite folder?" >&2
  exit 1
fi

SUITE_NAME="$(python3 -c "import json,sys; print(json.load(open('$SUITE_DIR/suite.json'))['name'])")"
CM_NAME="eval-suite-${SUITE_NAME}"

# Stage flattened files in a temp dir so --from-file produces the dotted keys.
STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT

cp "$SUITE_DIR/suite.json" "$STAGE/suite.json"
cp "$SUITE_DIR/dataset.json" "$STAGE/dataset.json"
if [[ -d "$SUITE_DIR/judges" ]]; then
  for f in "$SUITE_DIR/judges"/*; do
    [[ -e "$f" ]] || continue
    cp "$f" "$STAGE/judges.$(basename "$f")"
  done
fi

echo "Applying suite '$SUITE_NAME' as ConfigMap '$CM_NAME' in namespace '$NAMESPACE'..."
kubectl create configmap "$CM_NAME" \
  --namespace "$NAMESPACE" \
  --from-file="$STAGE" \
  --dry-run=client -o yaml | kubectl apply -f -

echo "Done. Keys:"
kubectl get configmap "$CM_NAME" -n "$NAMESPACE" -o jsonpath='{range .data}{"  "}{end}' 2>/dev/null || true
kubectl get configmap "$CM_NAME" -n "$NAMESPACE" -o go-template='{{range $k,$v := .data}}  {{$k}}{{"\n"}}{{end}}'
