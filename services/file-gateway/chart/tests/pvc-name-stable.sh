#!/usr/bin/env bash
# The PVC name must be stable across renders. It used to embed `now`, so every
# helm upgrade minted a new PVC and abandoned the previous one plus its EBS volume.
#
# Run: services/file-gateway/chart/tests/pvc-name-stable.sh
set -euo pipefail
CHART="$(cd "$(dirname "$0")/.." && pwd)"

name() { helm template fg "$CHART" ${1:+--set storage.pvcName="$1"} \
  | awk '/kind: PersistentVolumeClaim/{f=1} f&&/^  name:/{print $2; exit}'; }

A=$(name); sleep 1.1; B=$(name)   # >1s apart: a "20060102150405" suffix would differ
[ "$A" = "$B" ] || { echo "FAIL: PVC name unstable across renders: '$A' != '$B'"; exit 1; }
[ "$A" = "file-gateway-storage" ] || { echo "FAIL: expected 'file-gateway-storage', got '$A'"; exit 1; }

OVERRIDE=$(name "file-gateway-storage-20260510143032")
[ "$OVERRIDE" = "file-gateway-storage-20260510143032" ] || {
  echo "FAIL: storage.pvcName override ignored, got '$OVERRIDE'"; exit 1; }

echo "PASS: stable default '$A'; override honoured (existing releases can pin their PVC)"
