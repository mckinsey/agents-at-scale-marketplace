# Tasks: Introduce `executors/` Directory

## Tasks

- [ ] Move `services/executor-langchain/` → `executors/langchain/`
- [ ] Update `marketplace.json`: type → `"executor"`, documentation URL → `executors/executor-langchain/`
- [ ] Update `.github/workflows/main-push.yaml`: change path in all 4 matrix entries
- [ ] Update `.github/workflows/pull-request.yaml`: change path in both matrix entries
- [ ] Update `.github/release-please-config.json`: rename key to `executors/langchain`
- [ ] Update `.github/release-please-manifest.json`: rename key to `executors/langchain`
- [ ] Update `docs/content/services/_meta.js`: remove `executor-langchain` entry
- [ ] Create `docs/content/executors/_meta.js` with `langchain: 'LangChain Executor'`
