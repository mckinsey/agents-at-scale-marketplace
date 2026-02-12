# UBO Web Tools MCP Server

MCP server for web-based Ultimate Beneficial Owner research using search providers.

## Tools Exposed

| Tool | Description |
|------|-------------|
| `research_ubo_web` | Research UBOs using Perplexity or Tavily |
| `get_web_research_results` | Retrieve full results from storage |
| `list_web_evidence` | List all source URLs for a case |

## Setup

### 1. Ensure AI Gateway Secret Exists

The web tools use the same `aigw-secret` as the PDF tools (AI Gateway tokens work for all providers):

```bash
# If not already created:
kubectl create secret generic aigw-secret \
  --from-literal=base-url=YOUR_AIGW_BASE_URL \
  --from-literal=api-key=YOUR_AIGW_API_KEY
```

### 2. Build Docker Image

```bash
cd /path/to/ubo-resolver
docker build -f mcp-servers/ubo-web-tools/Dockerfile -t ubo-web-tools:latest .
```

### 3. Deploy to Kubernetes

```bash
kubectl apply -f mcp-servers/ubo-web-tools/k8s-direct.yaml
```

### 4. Deploy Agent

```bash
kubectl apply -f agents/ubo-web-agent.yaml
```

## Output Structure

The `research_ubo_web` tool returns:

```json
{
  "case_id": "abc123def456",
  "target_company": "Heineken N.V.",
  "ownership_table": [
    {
      "owner": "Mrs. C.L. de Carvalho-Heineken",
      "owned": "Heineken N.V.",
      "ownership_pct": 50.005,
      "voting_pct": 50.005,
      "type": "indirect",
      "sources": [{"url": "...", "title": "..."}],
      "snippet": "..."
    }
  ],
  "ubos": [
    {"name": "Mrs. C.L. de Carvalho-Heineken", "identified_as_ubo": true}
  ],
  "sources": [
    {"url": "https://...", "title": "...", "source_name": "..."}
  ],
  "summary": {
    "total_relations": 5,
    "ubo_count": 2,
    "source_count": 3
  }
}
```

## Evidence Storage

Results are stored in the storage layer:

```
artifacts/{case_id}/
  ├── analysis.json      # Full research results
  └── evidence/
      └── sources.json   # Source URLs and raw response
```

## Providers

### Perplexity (Recommended)
- Better at synthesizing information from multiple sources
- Provides citations automatically
- Models: `sonar` (fast), `sonar-pro` (thorough)

### Tavily
- Good for domain-specific searches
- Supports include/exclude domains
- Better for SEC filings, specific registries
