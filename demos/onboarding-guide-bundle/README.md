# Onboarding Guide Bundle

An Argo workflow that turns **any public git URL** into three artifacts a new joiner actually needs: a structural `analysis.md`, a new-joiner `ONBOARDING.md`, and a `TICKET.md` proposing a good first issue. The demo spans three execution engines — **Claude Agent SDK** at both ends (clone + ticket), **OpenAI Responses** in the middle (live web research), and the built-in completions executor for analysis + writing.

## What's included

**5 agents** wired to three execution engines:

| Agent | Execution engine | Model | What it does |
|---|---|---|---|
| `repo-reader-claude-sdk` | Claude Agent SDK | Claude Haiku (`anthropic`) | `git clone --depth 1` the URL into its sandbox; return the stack hint, file tree, and full contents of every source file as text |
| `code-analyzer-completions` | default completions (+ filesystem MCP) | `default` | consumes `repo-reader`'s dump via `prev-query`, produces the structural analysis, AND writes it to `output/<workflow-name>/analysis.md` |
| `research-buddy-openai-responses` | OpenAI Responses (+ `web_search_preview`) | `responses` | takes the stack hint, searches the live web for docs / quickstarts / pitfalls |
| `onboarding-writer-completions` | default completions (+ filesystem MCP) | `default` | synthesises the analysis + research and writes `output/<workflow-name>/ONBOARDING.md` |
| `ticket-suggester-claude-sdk` | Claude Agent SDK | Claude Haiku (`anthropic`) | proposes a good-first-ticket from the analysis; a small non-agent Argo step (`write-ticket`) uploads the result to `output/<workflow-name>/TICKET.md` |

Plus the supporting chart resources:

- **`file-gateway`** (Helm dependency — provides filesystem MCP for writes + HTTP API for downloads)
- **Argo Workflow RBAC** (ServiceAccount + Role + RoleBinding so the workflow can create `Query` CRs)
- **`MCPServer/mcp-filesystem`** CR pointing at `file-gateway-filesystem-mcp`
- **Anthropic `Model` CR** and a Secret created from `anthropic.apiKey`
- **`WorkflowTemplate/onboarding-generate`** (Argo) with the five-step DAG

## Prerequisites

- Ark cluster with the default completions executor ready.
- Argo Workflows installed.
- The two marketplace executors installed (this bundle does not install them):
  ```bash
  ark install marketplace/executors/executor-openai-responses --marketplace-version 0.1.3 -y
  ark install marketplace/executors/executor-claude-agent-sdk -y
  ```
  Pin `executor-openai-responses` to `0.1.3` — `0.1.4` ships a broken build (see the marketplace issue tracker).
- **Models already in the target namespace:**
  - `default` — any completions-compatible Model (the Ark cluster default).
  - `responses` — OpenAI Responses-compatible Model (provider: `openai`).
  - (The chart creates the third one, `anthropic`, from `anthropic.apiKey` or an existing Secret.)
- An **Anthropic API key** for the Claude Agent SDK agents.

## Install

Install in any namespace (default if omitted). If file-gateway is already present in the namespace (for example from another demo bundle), set `USE_EXISTING_FILE_GATEWAY=true` to skip installing it.

```bash
cd agents-at-scale-marketplace/demos/onboarding-guide-bundle
export ANTHROPIC_API_KEY=...
make build
make install-with-argo
```

To pin against a pre-existing `anthropic-api-key` Secret instead of passing the key at install time, install with:

```bash
helm upgrade --install onboarding-guide-bundle chart \
  --namespace default \
  --set anthropic.existingSecretName=my-existing-secret
```

## Run the workflow

From the Ark dashboard: open **Workflow Templates**, pick `onboarding-generate`, click Run, and fill in the `repo-url` parameter.

From the CLI:

```bash
make onboarding-demo REPO_URL=https://github.com/karpathy/micrograd
```

or directly:

```bash
kubectl create -f - <<'EOF'
apiVersion: argoproj.io/v1alpha1
kind: Workflow
metadata:
  generateName: onboarding-
spec:
  workflowTemplateRef:
    name: onboarding-generate
  arguments:
    parameters:
      - name: repo-url
        value: https://github.com/<owner>/<repo>
EOF
```

## Fetch the output

Each run writes to its own `output/<workflow-name>/` folder on file-gateway. Pull both the analysis and the onboarding guide to your laptop:

```bash
make fetch-output WF=<workflow-name>        # or: ./scripts/fetch-output.sh <workflow-name>
./scripts/fetch-output.sh                   # no arg = latest run
open ./output/<workflow-name>/ONBOARDING.md
```

## Uninstall

```bash
make uninstall
```

## DAG at a glance

```
         ┌─────────────────────────────────────────┐
         │ repo-reader-claude-sdk (Claude Agent SDK)│
         │ git clone + read → text dump             │
         └──────┬──────────────────────────────────┘
                │
       ┌────────┴────────┐
       ▼                 ▼
┌─────────────────┐  ┌────────────────────────────────┐
│ code-analyzer-   │  │ research-buddy-openai-responses│
│ completions      │  │ (OpenAI Responses + web search)│
│ writes analysis  │  │                                │
└──────┬───────────┘  └───────────────┬────────────────┘
       └─────────────┬────────────────┘
                     ▼
         ┌───────────────────────────────┐
         │ onboarding-writer-completions │
         │ writes ONBOARDING.md          │
         └──────────┬────────────────────┘
                    ▼
         ┌───────────────────────────────┐
         │ ticket-suggester-claude-sdk   │
         │ (Claude Agent SDK)            │
         └──────────┬────────────────────┘
                    ▼
         ┌───────────────────────────────┐
         │ write-ticket (Argo script)    │
         │ uploads TICKET.md             │
         └───────────────────────────────┘
```

## Notes

- **Why two executors for Claude work?** Claude Agent SDK runs Claude Code's bundled toolchain (Bash / Read / Glob) inside its own pod sandbox, so it can `git clone` and read arbitrary files — but it cannot reach the cluster-side filesystem MCP. The default completions executor *can* reach it but lacks a shell. This bundle uses both: Claude Agent SDK for fetching and for ticket suggestion, and the default executor (with Claude Haiku via the Anthropic `Model`) for the analysis/writing steps that need MCP.
- **Why an extra `write-ticket` step?** `ticket-suggester-claude-sdk` returns its proposal as text. A small alpine + kubectl + curl Argo step reads the Query response and POSTs it to file-gateway so it lands alongside the other artifacts.
- **Output folder per run:** `output/<workflow-name>/` is derived from `{{workflow.name}}` at run time. Runs do not overwrite each other.
