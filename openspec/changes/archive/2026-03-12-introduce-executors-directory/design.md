# Design: Introduce `executors/` Directory

## Approach

This is a structural refactor — no code changes inside the executor itself. The work is moving one directory and updating all references to its path.

## Directory Convention

Top-level directories map 1:1 to marketplace item types:

```
agents/     → type: "agent"
demos/      → type: "demo"
executors/  → type: "executor"    ← new
mcps/       → type: "mcp"
services/   → type: "service"
```

Within `executors/`, each subdirectory is named after the framework (short name). The globally-unique identifier uses the `executor-` prefix:

```
executors/
└── langchain/          ← dir name: framework
    ├── chart/          ← chart name: executor-langchain
    ├── src/
    ├── Dockerfile
    ├── devspace.yaml
    ├── pyproject.toml
    └── ...
```

## Naming Rules for Future Executors

| Framework | Directory | Marketplace Name | Chart OCI |
|-----------|-----------|-----------------|-----------|
| LangChain | `executors/langchain` | `executor-langchain` | `charts/executor-langchain` |
| CrewAI | `executors/crewai` | `executor-crewai` | `charts/executor-crewai` |
| AutoGen | `executors/autogen` | `executor-autogen` | `charts/executor-autogen` |

## Release-Please Consideration

Release-please uses the directory path as the package key in both config and manifest. When renaming:
- Old key `services/executor-langchain` → new key `executors/langchain`
- Package name stays `executor-langchain`
- Version carries over (`0.1.2`)
- CHANGELOG moves with the directory

## Docs Structure

Mirror the top-level convention in docs:

```
docs/content/
├── agents/
├── executors/        ← new
│   └── _meta.js
├── mcps/
└── services/
    └── _meta.js      ← remove executor-langchain entry
```
