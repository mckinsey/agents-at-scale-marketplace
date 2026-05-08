# Lightweight PDF Extraction MCP Server

Minimal replacement for ubo-pdf-tools with ~200 lines of code.

## Features

- **analyze_pdf_ownership**: Extract ownership information from PDFs using LLM
- **scout_pdf_for_ownership**: Find pages with ownership-related keywords
- **get_analysis_results**: Compatibility stub (stateless)

## Quick Start

```bash
# Build Docker image
docker build -t pdf-extraction-mcp:latest .

# Create secret with LLM API key
kubectl create secret generic ai-gateway-azure-openai \
  --from-literal=token=YOUR_KEY

# Deploy to Kubernetes
helm install pdf-extraction-mcp ./chart -n default --create-namespace

# Verify
kubectl get mcpserver pdf-extraction-mcp
kubectl get pods -l app.kubernetes.io/name=pdf-extraction-mcp
```

## Configuration

LLM credentials are read from a Kubernetes Secret (default name `ai-gateway-azure-openai`, key `token`). Override the secret name and key via `llm.apiKeySecret.name` / `llm.apiKeySecret.key` in `values.yaml`.

| Variable | Description | Default |
|----------|-------------|---------|
| `LLM_PROVIDER` | `openai` or `anthropic` | `openai` |
| `LLM_MODEL` | Model name | `gpt-4o` |
| `LLM_BASE_URL` | API base URL | _(Azure AI gateway)_ |
| `LLM_API_KEY` | API key (from secret above) | _(required)_ |

### Storage

By default the chart deploys without a data volume — the MCP server runs but tools that read files from `/data` will only see what's already in the container. To share storage with `file-gateway` (recommended when running the KYC bundle):

```bash
helm install pdf-extraction-mcp ./chart \
  --set dataVolume.enabled=true \
  --set dataVolume.claimName=file-gateway-storage
```

## Dependencies

- mcp>=1.0.0
- pymupdf>=1.26.0 (PDF parsing)
- httpx>=0.27.0 (HTTP client)

Total: 4 dependencies, ~200 lines of code

## Tool Usage

```yaml
# In agent YAML
tools:
  - type: mcp
    name: pdf-extraction-mcp-analyze-pdf-ownership
```

## Limitations

- Stateless (no result caching)
- Simple chunking (first 16k chars)
- No UBO computation (returns raw ownership data)
- No graph visualization
