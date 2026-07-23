#!/usr/bin/env bash
#
# Renders the argo-make-author chart and asserts that every entry in the
# Agent's spec.tools has a supported `type` and a non-empty `name`.
#
# The Agent carries the label ark.mckinsey.com/skip-webhook-validation: "true"
# to stop the mutating webhook from injecting a default modelRef. That label
# also disables the validating webhook, so its tool checks (type/name) never
# run at admission. This test is the safety net: it catches an unsupported
# tool type or a missing name before the chart is checked in.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CHART_DIR="$(cd "${SCRIPT_DIR}/../chart" && pwd)"

# Supported tool types, derived from the Ark Agent tool schema as used across
# the marketplace charts (built-in, custom, mcp).
SUPPORTED_TYPES="built-in custom mcp"

echo "Rendering ${CHART_DIR}/templates/agent.yaml ..."
RENDERED="$(helm template argo-make-author "${CHART_DIR}" --show-only templates/agent.yaml)"

RENDERED="${RENDERED}" SUPPORTED_TYPES="${SUPPORTED_TYPES}" python3 - <<'PY'
import os
import sys
import yaml

supported = set(os.environ["SUPPORTED_TYPES"].split())
rendered = os.environ["RENDERED"]

docs = [d for d in yaml.safe_load_all(rendered) if d]
agents = [d for d in docs if d.get("kind") == "Agent"]

if not agents:
    print("FAIL: no Agent resource rendered from agent.yaml")
    sys.exit(1)

errors = []
checked = 0

for agent in agents:
    name = agent.get("metadata", {}).get("name", "<unknown>")
    tools = agent.get("spec", {}).get("tools", [])
    if not tools:
        errors.append(f"Agent '{name}': spec.tools is empty or missing")
        continue
    for i, tool in enumerate(tools):
        checked += 1
        ttype = tool.get("type")
        tname = tool.get("name")
        if ttype not in supported:
            errors.append(
                f"Agent '{name}' tool[{i}]: type '{ttype}' is not supported "
                f"(allowed: {', '.join(sorted(supported))})"
            )
        if not tname or not str(tname).strip():
            errors.append(f"Agent '{name}' tool[{i}] (type '{ttype}'): name is empty or missing")

if errors:
    print("FAIL: tool schema validation errors:")
    for e in errors:
        print(f"  - {e}")
    sys.exit(1)

print(f"PASS: {checked} tool(s) validated, all have a supported type and a non-empty name")
PY
