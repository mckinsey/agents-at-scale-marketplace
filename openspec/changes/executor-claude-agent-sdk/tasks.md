## 1. Project Scaffolding

- [ ] 1.1 Create `executors/claude-agent-sdk/` directory structure: `src/claude_agent_executor/`, `chart/templates/`, `tests/`
- [ ] 1.2 Create `pyproject.toml` with dependencies: `claude-agent-sdk`, `openinference-instrumentation-claude-agent-sdk`, `opentelemetry-sdk`, `opentelemetry-exporter-otlp`, `ark-sdk`, `a2a-sdk`, `fastapi`, `uvicorn`
- [ ] 1.3 Create `Dockerfile` following langchain executor pattern (python:3.12-slim, uv, non-root UID 1001, port 8000)

## 2. Core Executor

- [ ] 2.1 Create `src/claude_agent_executor/__init__.py` and `__main__.py` entry point
- [ ] 2.2 Create `src/claude_agent_executor/app.py` — `ExecutorApp` wrapping `ClaudeAgentExecutor`
- [ ] 2.3 Create `src/claude_agent_executor/executor.py` — `ClaudeAgentExecutor(BaseExecutor)` with: session directory creation at `/data/sessions/<conversationId>/`, `ClaudeSDKClient` init with `cwd` and optional `resume`, response collection from `receive_response()`, `ANTHROPIC_MODEL` env var with default

## 3. OTEL Instrumentation

- [ ] 3.1 Add conditional OTEL init in executor: check `OTEL_EXPORTER_OTLP_ENDPOINT`, create `TracerProvider` + `OTLPSpanExporter` + `BatchSpanProcessor`, call `ClaudeAgentSDKInstrumentor().instrument()`

## 4. Helm Chart

- [ ] 4.1 Create `chart/Chart.yaml` (name: `executor-claude-agent-sdk`, type: application, v0.1.0)
- [ ] 4.2 Create `chart/values.yaml` with: image repo, env config (`HOST`, `PORT`, `ANTHROPIC_MODEL`), resource limits, service config, PVC config, healthCheck, securityContext
- [ ] 4.3 Create `chart/templates/deployment.yaml` with: `envFrom` for `anthropic-api-key` secret and `otel-environment-variables` secret (optional), volumeMount for `/data/sessions`, liveness/readiness probes at `/health`
- [ ] 4.4 Create `chart/templates/pvc.yaml` for `executor-claude-agent-sdk-sessions` PersistentVolumeClaim
- [ ] 4.5 Create `chart/templates/service.yaml` (ClusterIP, port 8000)
- [ ] 4.6 Create `chart/templates/serviceaccount.yaml` and `chart/templates/rbac.yaml` (read access to ARK CRDs + secrets)
- [ ] 4.7 Create `chart/templates/executionengine.yaml` (ExecutionEngine CRD with serviceRef)
- [ ] 4.8 Create `chart/templates/httproute.yaml` (optional Gateway API route)

## 5. DevSpace

- [ ] 5.1 Create `devspace.yaml` with: image build config, Helm deployment, dev mode sync for `/src`, hot-reload command, hook for HTTPRoute CRD check

## 6. CI/CD Integration

- [ ] 6.1 Add matrix entry to `.github/workflows/main-push.yaml` for docker build and chart validate
- [ ] 6.2 Add matrix entry to `.github/workflows/pull-request.yaml` for docker build and chart validate
- [ ] 6.3 Add package entry to `.github/release-please-config.json`
- [ ] 6.4 Add version entry to `.github/release-please-manifest.json` (`"executors/claude-agent-sdk": "0.1.0"`)

## 7. Marketplace & Documentation

- [ ] 7.1 Add executor entry to `marketplace.json` with type `executor`, chart path, service details
- [ ] 7.2 Create `docs/content/executors/claude-agent-sdk.mdx` covering: install methods, secrets setup, PVC config, agent creation, session behavior, OTEL setup, tool permissions
- [ ] 7.3 Update `docs/content/executors/_meta.js` with nav entry for claude-agent-sdk
- [ ] 7.4 Create `executors/claude-agent-sdk/README.md` with quick start and overview
