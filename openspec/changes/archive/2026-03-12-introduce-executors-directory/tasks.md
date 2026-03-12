# Tasks: Introduce `executors/` Directory

## Tasks

- [x] Move `services/executor-langchain/` → `executors/langchain/`
- [x] Update `marketplace.json`: type → `"executor"`, documentation URL → `executors/executor-langchain/`
- [x] Update `.github/workflows/main-push.yaml`: change path in all 4 matrix entries
- [x] Update `.github/workflows/pull-request.yaml`: change path in both matrix entries
- [x] Update `.github/release-please-config.json`: rename key to `executors/langchain`
- [x] Update `.github/release-please-manifest.json`: rename key to `executors/langchain`
- [x] Update `docs/content/services/_meta.js`: remove `executor-langchain` entry
- [x] Create `docs/content/executors/_meta.js` with `langchain: 'LangChain Executor'`
