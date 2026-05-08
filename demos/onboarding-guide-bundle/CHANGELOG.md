# Changelog

## 0.1.0

- Initial release.
- Five-agent Argo workflow that generates `analysis.md`, `ONBOARDING.md`, and `TICKET.md` from any public git URL.
- Uses the Claude Agent SDK executor (git clone + ticket proposal), the OpenAI Responses executor (web search), and the default completions executor (analysis + writing via file-gateway MCP).
- Per-run `output/<workflow-name>/` folders on file-gateway so runs don't overwrite each other.
- `fetch-output.sh` defaults to the latest workflow.
- RBAC + ServiceAccount for Argo Workflows to create `Query` CRs.
