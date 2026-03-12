# Introduce `executors/` Top-Level Directory

## Summary

Create a new `executors/` root directory following the repo's convention where top-level directories map 1:1 to marketplace item types. Move `services/executor-langchain` into `executors/langchain` and introduce the `"executor"` type in `marketplace.json`.

## Motivation

The `services/` directory is becoming a catch-all. Execution engines (runtimes that run agent logic) are fundamentally different from infrastructure services (observability, storage, dev tools). With more executors expected (CrewAI, AutoGen, Semantic Kernel, etc.), a dedicated category gives them a clear home and makes the taxonomy self-documenting.

## What Changes

### Directory structure

```
BEFORE                              AFTER
services/                           services/
├── a2a-inspector/                  ├── a2a-inspector/
├── ark-sandbox/                    ├── ark-sandbox/
├── executor-langchain/  ← move    ├── file-gateway/
├── file-gateway/                   ├── langfuse/
├── langfuse/                       ├── mcp-inspector/
├── mcp-inspector/                  └── phoenix/
└── phoenix/                        executors/          ← NEW
                                    └── langchain/      ← moved here
```

### Naming convention

| Attribute | Value |
|-----------|-------|
| Directory | `executors/langchain/` |
| Marketplace name | `executor-langchain` (unchanged) |
| Marketplace type | `"executor"` (was `"service"`) |
| Chart OCI path | `charts/executor-langchain` (unchanged) |
| Helm release name | `executor-langchain` (unchanged) |
| K8s resource names | `executor-langchain` (unchanged) |

Future executors follow the same pattern: `executors/crewai` → name `executor-crewai`, chart `charts/executor-crewai`.

### Files to update

1. **Move directory**: `services/executor-langchain/` → `executors/langchain/`
2. **`marketplace.json`**: Change type to `"executor"`, update documentation URL
3. **`.github/workflows/main-push.yaml`**: Update path in 4 matrix entries (build-docker-images, validate-charts, push-docker-images, deploy-charts)
4. **`.github/workflows/pull-request.yaml`**: Update path in 2 matrix entries (build-docker-images, validate-charts)
5. **`.github/release-please-config.json`**: Change key from `services/executor-langchain` to `executors/langchain`
6. **`.github/release-please-manifest.json`**: Change key from `services/executor-langchain` to `executors/langchain`
7. **`docs/content/services/_meta.js`**: Remove `executor-langchain` entry
8. **`docs/content/executors/_meta.js`**: Create with `langchain` entry

### What does NOT change

- Package name (`executor-langchain`)
- Helm chart name and OCI path
- K8s service/deployment names
- Helm release name
- Any internal code within the executor itself

## Risks

- **Release-please path change**: release-please tracks versions by directory path. Changing the path key in config and manifest should work cleanly, but the version history in the old path is effectively "reset" from release-please's perspective. The CHANGELOG stays with the moved directory.
- **Open PRs**: Any in-flight PRs touching `services/executor-langchain` will need rebasing.
