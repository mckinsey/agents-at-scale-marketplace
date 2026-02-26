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

# Deploy to Kubernetes
kubectl apply -f k8s-deployment.yaml

# Verify
kubectl get mcpserver pdf-extraction-mcp
kubectl get pods -l app=pdf-extraction-mcp
```

## Configuration

Set via Kubernetes Secret `ai-gateway-azure-openai`:
- `LLM_PROVIDER`: openai or anthropic (default: openai)
- `LLM_MODEL`: Model name (default: gpt-4)
- `LLM_BASE_URL`: API base URL (optional)
- `LLM_API_KEY`: API key (required)

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
