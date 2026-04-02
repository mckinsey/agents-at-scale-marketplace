# CLAUDE.md

## What This Repo Is

The Ark Marketplace is the add-on ecosystem for [Ark core](https://github.com/mckinsey/agents-at-scale-ark). It provides executors, services, MCP servers, agents, and demo bundles that extend Ark's native capabilities.

**Dependency direction**: Marketplace items depend on Ark core — never the other way around. Core Ark defines contracts (CRDs, SDK interfaces, A2A protocol) and knows nothing about specific marketplace items. Before building something here, check whether Ark core already provides the capability natively.

**Isolation**: Each marketplace item must be independently deployable with no dependencies on other marketplace items. Avoid introducing cross-item dependencies. When a dependency is unavoidable, it must be declared explicitly in `marketplace.json` — implicit coupling or shared state between items is not allowed.

## Component Types

| Type | What it extends | Example |
|------|----------------|---------|
| **Executors** (`executors/`) | Implement `BaseExecutor` from `ark-sdk` to run agent workloads via A2A | Claude Agent SDK, LangChain |
| **Services** (`services/`) | Infrastructure add-ons deployed alongside Ark | Phoenix, Langfuse, ark-sandbox, file-gateway |
| **MCP Servers** (`mcps/`) | Tool providers registered as `MCPServer` CRDs | Filesystem, speech, PDF extraction, web research |
| **Agents** (`agents/`) | Pre-built agents using Ark core CRDs | Noah (runtime administration) |
| **Demos** (`demos/`) | Solution bundles composing agents, teams, tools, and workflows | KYC onboarding, COBOL modernization |

## Structure

Each component follows this pattern:

```
<component>/
├── chart/              # Helm chart (Chart.yaml, values.yaml, templates/)
├── devspace.yaml       # Local development config
├── Dockerfile          # Container image (if custom)
├── README.md           # Terse, developer-focused
└── src/                # Source code
```

Other key files:
- **`marketplace.json`** at repo root — registry of all items with metadata for `ark install` discovery
- **`docs/`** — Documentation site (Next.js + Nextra), content in `docs/content/` as MDX
- **`openspec/`** — Spec-driven design documents and archived change proposals

## Build Patterns

### Deployment (all components)
```bash
# Using Ark CLI
ark install marketplace/<type>/<name>

# Using DevSpace (local dev)
cd <component>/
devspace dev

# Using Helm directly
cd <component>/
helm install <name> ./chart -n <namespace> --create-namespace
```

Check each component's README for language-specific build and test instructions.

## Conventions

Inherited from [Ark core](https://github.com/mckinsey/agents-at-scale-ark/blob/main/CLAUDE.md):

- **Naming**: Always "Ark", never "ARK"
- **Writing style**: Concise and direct. No filler adjectives. READMEs are terse, focused on developer setup.
- **Commits**: Conventional commit format required (`feat:`, `fix:`, `docs:`, `chore:`, etc.)
- **Deployments**: Helm + DevSpace for all Kubernetes deployments
- **CI/CD**: Reusable GitHub Actions workflows for charts, Docker images, docs, and PR title validation
- **Versioning**: Semantic versioning via Release Please with conventional commits

## Integration Contracts

### Executors
Subclass `BaseExecutor` from `ark-sdk`, wrap with `ExecutorApp`. The Helm chart registers an `ExecutionEngine` CRD. Communication is via A2A protocol. Agents reference the executor via `spec.executionEngine.name`.

### MCP Servers
Deploy as a service, register an `MCPServer` CRD. Tools are auto-generated with a name prefix (e.g., `mcp-filesystem-read-file`). Agents reference individual tools in `spec.tools`.

### Demos
Helm charts that deploy agents, teams, tools, and optionally Argo WorkflowTemplates. Dependencies on other marketplace items (e.g., file-gateway, MCP servers) are declared in `marketplace.json`.
