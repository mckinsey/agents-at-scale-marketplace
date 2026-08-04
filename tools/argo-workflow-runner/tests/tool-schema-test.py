#!/usr/bin/env python3
#
# Renders the argo-workflow-runner chart and asserts that every Tool resource
# is a well-formed HTTP tool: spec.type is "http", it has a non-empty
# http.url / http.method, and - critically for the security posture - the
# submit tool hardcodes resourceKind: WorkflowTemplate in its body so the model
# can never submit an arbitrary workflow kind.

import json
import subprocess
import sys
from pathlib import Path

import yaml

SCRIPT_DIR = Path(__file__).resolve().parent
CHART_DIR = (SCRIPT_DIR / ".." / "chart").resolve()

ALLOWED_METHODS = {"GET", "POST", "PUT", "DELETE", "PATCH"}


def render() -> str:
    print(f"Rendering {CHART_DIR} ...")
    result = subprocess.run(
        [
            "helm",
            "template",
            "argo-workflow-runner",
            str(CHART_DIR),
            "--set",
            "auth.token=test-token",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def validate(rendered: str) -> int:
    docs = [d for d in yaml.safe_load_all(rendered) if d]
    tools = [d for d in docs if d.get("kind") == "Tool"]

    if len(tools) != 3:
        print(f"FAIL: expected 3 Tool resources, rendered {len(tools)}")
        return 1

    errors = []
    for tool in tools:
        name = tool.get("metadata", {}).get("name", "<unknown>")
        spec = tool.get("spec", {})
        if spec.get("type") != "http":
            errors.append(f"Tool '{name}': spec.type is '{spec.get('type')}', expected 'http'")
        http = spec.get("http", {})
        url = http.get("url")
        method = http.get("method")
        if not url or not str(url).startswith(("http://", "https://")):
            errors.append(f"Tool '{name}': http.url is missing or not an http(s) URL: {url!r}")
        if method not in ALLOWED_METHODS:
            errors.append(f"Tool '{name}': http.method '{method}' is not one of {sorted(ALLOWED_METHODS)}")

    submit = next((t for t in tools if t["spec"].get("http", {}).get("url", "").endswith("/submit")), None)
    if submit is None:
        errors.append("no submit tool (url ending in /submit) was rendered")
    else:
        body = submit["spec"]["http"].get("body", "")
        if '"resourceKind":"WorkflowTemplate"' not in body.replace(" ", ""):
            errors.append("submit tool body must hardcode resourceKind: WorkflowTemplate")
        if "resourceKind" in json.dumps(submit["spec"].get("inputSchema", {})):
            errors.append("submit tool must not expose resourceKind as a model input")

    if errors:
        print("FAIL: tool schema validation errors:")
        for e in errors:
            print(f"  - {e}")
        return 1

    print(f"PASS: {len(tools)} HTTP tool(s) validated; submit tool pins resourceKind to WorkflowTemplate")
    return 0


def main() -> int:
    return validate(render())


if __name__ == "__main__":
    sys.exit(main())
