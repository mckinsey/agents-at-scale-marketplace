# Lightweight Web Research MCP Server

Minimal replacement for ubo-web-tools with ~100 lines of code.

## Features

- **research_ubo_web**: Search web for ownership information using Tavily or Perplexity
- **get_web_research_results**: Compatibility stub (stateless)
- **list_web_evidence**: Compatibility stub (stateless)

## Quick Start

```bash
# Build Docker image
docker build -t web-research-mcp:latest .

# Create secret with API keys
kubectl create secret generic web-search-credentials \
  --from-literal=tavily-api-key=YOUR_KEY

# Deploy to Kubernetes
kubectl apply -f k8s-deployment.yaml

# Verify
kubectl get mcpserver web-research-mcp
kubectl get pods -l app=web-research-mcp
```

## Configuration

Set via Kubernetes Secret `web-search-credentials`:
- `SEARCH_PROVIDER`: tavily or perplexity (default: tavily)
- `TAVILY_API_KEY`: Tavily API key
- `PERPLEXITY_API_KEY`: Perplexity API key

## Dependencies

- mcp>=1.0.0
- httpx>=0.27.0 (HTTP client)

Total: 2 dependencies, ~100 lines of code

## Tool Usage

```yaml
# In agent YAML
tools:
  - type: mcp
    name: web-research-mcp-research-ubo-web
```

## Limitations

- Stateless (no result caching)
- Basic result formatting
- No advanced extraction (returns raw search results)
