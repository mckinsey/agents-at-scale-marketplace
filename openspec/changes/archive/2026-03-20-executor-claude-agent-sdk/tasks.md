## 1. Project Scaffolding

- [x] 1.1 Create `executors/claude-agent-sdk/` directory structure: `src/claude_agent_executor/`, `chart/templates/`, `tests/`
- [x] 1.2 Create `pyproject.toml` with dependencies: `claude-agent-sdk`, `openinference-instrumentation-claude-agent-sdk`, `opentelemetry-sdk`, `opentelemetry-exporter-otlp`, `ark-sdk`, `a2a-sdk`, `fastapi`, `uvicorn`
- [x] 1.3 Create `Dockerfile` following langchain executor pattern (python:3.12-slim, uv, non-root UID 1001, port 8000)

## 2. Core Executor

- [x] 2.1 Create `src/claude_agent_executor/__init__.py` and `__main__.py` entry point
- [x] 2.2 Create `src/claude_agent_executor/app.py` — `ExecutorApp` wrapping `ClaudeAgentExecutor`
- [x] 2.3 Create `src/claude_agent_executor/executor.py` — `ClaudeAgentExecutor(BaseExecutor)` with: session directory creation at `/data/sessions/<conversationId>/`, `ClaudeSDKClient` init with `cwd` and optional `resume`, response collection from `receive_response()`, `ANTHROPIC_MODEL` env var with default

## 3. OTEL Instrumentation

- [x] 3.1 Add conditional OTEL init in executor: check `OTEL_EXPORTER_OTLP_ENDPOINT`, create `TracerProvider` + `OTLPSpanExporter` + `BatchSpanProcessor`, call `ClaudeAgentSDKInstrumentor().instrument()`

## 4. Helm Chart

- [x] 4.1 Create `chart/Chart.yaml` (name: `executor-claude-agent-sdk`, type: application, v0.1.0)
- [x] 4.2 Create `chart/values.yaml` with: image repo, env config (`HOST`, `PORT`, `ANTHROPIC_MODEL`), resource limits, service config, PVC config, healthCheck, securityContext
- [x] 4.3 Create `chart/templates/deployment.yaml` with: `envFrom` for `anthropic-api-key` secret and `otel-environment-variables` secret (optional), volumeMount for `/data/sessions`, liveness/readiness probes at `/health`
- [x] 4.4 Create `chart/templates/pvc.yaml` for `executor-claude-agent-sdk-sessions` PersistentVolumeClaim
- [x] 4.5 Create `chart/templates/service.yaml` (ClusterIP, port 8000)
- [x] 4.6 Create `chart/templates/serviceaccount.yaml` and `chart/templates/rbac.yaml` (read access to ARK CRDs + secrets)
- [x] 4.7 Create `chart/templates/executionengine.yaml` (ExecutionEngine CRD with serviceRef)
- [x] 4.8 Create `chart/templates/httproute.yaml` (optional Gateway API route)

## 5. DevSpace

- [x] 5.1 Create `devspace.yaml` with: image build config, Helm deployment, dev mode sync for `/src`, hot-reload command, hook for HTTPRoute CRD check

## 6. CI/CD Integration

- [x] 6.1 Add matrix entry to `.github/workflows/main-push.yaml` for docker build and chart validate
- [x] 6.2 Add matrix entry to `.github/workflows/pull-request.yaml` for docker build and chart validate
- [x] 6.3 Add package entry to `.github/release-please-config.json`
- [x] 6.4 Add version entry to `.github/release-please-manifest.json` (`"executors/claude-agent-sdk": "0.1.0"`)

## 7. Marketplace & Documentation

- [x] 7.1 Add executor entry to `marketplace.json` with type `executor`, chart path, service details
- [x] 7.2 Create `docs/content/executors/claude-agent-sdk.mdx` covering: install methods, secrets setup, PVC config, agent creation, session behavior, OTEL setup, tool permissions
- [x] 7.3 Update `docs/content/executors/_meta.js` with nav entry for claude-agent-sdk
- [x] 7.4 Create `executors/claude-agent-sdk/README.md` with quick start and overview
