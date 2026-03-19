# Evaluator

AI evaluation service with LLM-as-a-Judge, deterministic metrics, RAGAS, and Langfuse. Runs standalone or alongside the Ark operator.

## Quickstart

```bash
make help
make install
make dev
```

## Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `DEFAULT_MODEL_ENDPOINT` | LLM API base URL | `https://api.openai.com/v1` |
| `DEFAULT_MODEL_API_KEY` | LLM API key | `demo-key` |
| `DEFAULT_MODEL_NAME` | Model name | `gpt-4o-mini` |
| `KUBERNETES_INTEGRATION` | Enable K8s features (query, event eval) | `true` |

## API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/evaluate` | POST | LLM-as-a-Judge evaluation |
| `/evaluate-metrics` | POST | Deterministic metrics evaluation |
| `/providers/{provider}/metrics` | GET | List provider metrics |
| `/health` | GET | Health check |
| `/ready` | GET | Readiness check |

## Evaluation Types

- **direct** — Evaluate an input/output pair (no K8s required)
- **baseline** — Test model against golden examples (no K8s required)
- **query** — Evaluate an Ark Query CRD response (requires Ark)
- **event** — Expression-based K8s event evaluation (requires Ark)
- **batch** — Aggregate multiple evaluations (requires Ark)

## Providers

- `ark` (default) — LLM-as-a-Judge using configured model endpoint
- `ragas` — Standalone RAGAS metric evaluation
- `langfuse` — RAGAS evaluation with Langfuse tracing

## Development

```bash
# Install dependencies
uv sync --extra all --extra dev

# Run locally
PYTHONPATH=src uv run python -m evaluator

# Run tests
PYTHONPATH=src uv run pytest tests/ -v
```
