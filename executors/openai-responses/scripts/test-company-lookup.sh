#!/usr/bin/env bash
set -e

kubectl delete agent company-lookup-agent query company-lookup-query 2>/dev/null || true
kubectl apply -f "$(dirname "$0")/../examples/company-lookup-agent.yaml"
"$(dirname "$0")/test-cluster.sh" --agent company-lookup-agent --input "ADAM GROOMING BN LTD"
