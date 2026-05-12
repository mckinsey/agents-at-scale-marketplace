# Perplexity Ask MCP Server

Exposes the Perplexity API (conversational AI with real-time web search) as a single MCP tool.

## Features

- **ask**: Send a chat-style `messages` array to Perplexity and return the model's response

## Quick Start

```bash
# Build Docker image
docker build -t perplexity-ask-mcp:latest .

# Create secret with Perplexity API key
kubectl create secret generic web-search-credentials \
  --from-literal=perplexity-api-key=YOUR_KEY

# Deploy with Helm
helm install perplexity-ask-mcp ./chart -n default --create-namespace

# Verify
kubectl get mcpserver perplexity
kubectl get pods -l app.kubernetes.io/name=perplexity-ask-mcp
```

## Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `PERPLEXITY_API_KEY` | API key from [Perplexity](https://www.perplexity.ai/) (required) | _(unset)_ |
| `PERPLEXITY_MODEL` | Perplexity model name | `sonar` |
| `PERPLEXITY_BASE_URL` | Perplexity API base URL | `https://api.perplexity.ai` |

`PERPLEXITY_API_KEY` is read from Kubernetes Secret `web-search-credentials` (key `perplexity-api-key`). Override the secret name and key via `perplexity.apiKeySecret.name` / `perplexity.apiKeySecret.key` in `values.yaml`.

The chart registers the MCPServer as `perplexity` (via `mcpServer.nameOverride`), so Ark auto-generates a Tool named `perplexity-ask` — matching the LegacyX KYC demo's expected tool name.

## Tool Usage

```yaml
# In agent YAML
tools:
  - type: mcp
    name: perplexity-ask
```

## Local Run

```bash
export PERPLEXITY_API_KEY=your_key
pip install -r requirements.txt
python main.py
```

Server listens on port 8000; MCP endpoint at `/mcp` (streamable HTTP).

## Dependencies

- mcp>=1.0.0
- httpx>=0.27.0 (HTTP client)
- starlette>=0.40.0
- uvicorn>=0.30.0

## Limitations

- Requires a valid Perplexity API key (paid)
- Single tool (`ask`) — no streaming, no system-prompt management
