# UBO PDF Tools MCP Server

Production-grade MCP server for Ultimate Beneficial Owner (UBO) extraction from PDF documents.

## Overview

This MCP server exposes the UBO resolution pipeline as tools for ARK agents. It provides:

- PDF parsing and text extraction
- RAG-based ownership information retrieval
- LLM-powered ownership relation extraction
- UBO computation with effective ownership calculation
- Support for OpenAI and Anthropic models

## Architecture

- **Framework**: FastMCP with Streamable HTTP transport
- **Core Logic**: `ubo-resolver` Python packages (ubo_infra, ubo_domain, ubo_engine)
- **Transport**: HTTP/SSE for ARK compatibility
- **Deployment**: Kubernetes with Docker Desktop

## Prerequisites

- Kubernetes cluster (Docker Desktop K8s or similar)
- Docker for building images
- OpenAI or Anthropic API key
- Python 3.12+ (for local development)

## Quick Start

### 1. Build Docker Image

```bash
cd /path/to/ubo-resolver
docker build -f mcp-servers/ubo-pdf-tools/Dockerfile -t ubo-pdf-tools:latest .
```

### 2. Deploy to Kubernetes

```bash
# Using direct K8s manifests (recommended)
kubectl apply -f mcp-servers/ubo-pdf-tools/k8s-direct.yaml

# Verify deployment
kubectl get pods -l app=ubo-pdf-tools
kubectl get mcpserver ubo-pdf-tools-server
```

### 3. Configure API Keys

```bash
# Create secret for OpenAI
kubectl create secret generic openai-credentials \
  --from-literal=api-key="YOUR_OPENAI_API_KEY"

# Or for Anthropic
kubectl create secret generic anthropic-credentials \
  --from-literal=api-key="YOUR_ANTHROPIC_API_KEY"

# Update deployment to use the secret
kubectl edit deployment ubo-pdf-tools
```

### 4. Deploy Example Agent

```bash
kubectl apply -f mcp-servers/ubo-pdf-tools/examples/ubo-pdf-tools-agent.yaml
```

## MCP Tools

### `analyze_pdf_ownership`

Analyzes a PDF document to extract Ultimate Beneficial Owners (UBOs).

**Parameters:**
- `pdf_path` (string, required): Path to PDF file or HTTP(S) URL
- `target_company` (string, required): Full legal name of target company
- `extraction_model` (string, default: "gpt-4"): LLM model for extraction
- `extraction_provider` (string, default: "openai"): Provider (openai/anthropic)
- `num_passes` (int, default: 1): Number of extraction passes for voting
- `min_votes` (int, default: 1): Minimum votes to accept a relation
- `filter_self_loops` (bool, default: true): Remove self-loop relations
- `filter_voting_only` (bool, default: true): Remove voting-only relations
- `filter_subsidiaries` (bool, default: true): Filter subsidiary table patterns
- `min_confidence` (float, default: 0.0): Minimum confidence threshold
- `ubo_threshold` (float, default: 0.25): UBO ownership threshold (25%)

**Returns:**
- `entities`: List of entities with IDs, names, types, effective ownership
- `edges`: List of ownership edges with evidence
- `ubos`: List of identified UBO entity IDs
- `effective_ownership`: Map of entity ID to ownership percentage
- `metadata`: Pipeline execution metadata

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `FASTMCP_HOST` | No | `0.0.0.0` | Host to bind to |
| `FASTMCP_PORT` | No | `8080` | Port to bind to |
| `OPENAI_API_KEY` | Conditional | - | OpenAI API key |
| `OPENAI_BASE_URL` | No | - | Custom OpenAI base URL |
| `ANTHROPIC_API_KEY` | Conditional | - | Anthropic API key |
| `ANTHROPIC_BASE_URL` | No | - | Custom Anthropic base URL |

### Kubernetes Resources

Default resource requests/limits:
- CPU: 250m request, 1000m limit
- Memory: 256Mi request, 1Gi limit

### MCP Server Timeout

Default: 300s (5 minutes) - adjust in `k8s-direct.yaml` if needed for large PDFs.

## Local Development

### Setup

```bash
# From project root
cd /path/to/ubo-resolver

# Install dependencies
pip install -e .
pip install -r mcp-servers/ubo-pdf-tools/requirements.txt

# Set environment variables
export OPENAI_API_KEY="your-key"
export FASTMCP_HOST="0.0.0.0"
export FASTMCP_PORT="8080"
```

### Run Server

```bash
python mcp-servers/ubo-pdf-tools/main.py
```

Server will be available at `http://localhost:8080/mcp`

### Testing

```bash
# Test import paths
python -c "from ubo_infra.app.usecases import create_case_context; print('OK')"

# Test server startup
curl http://localhost:8080/mcp
```

## Deployment

### Docker Desktop Kubernetes

The provided manifests are optimized for Docker Desktop K8s:
- `imagePullPolicy: Never` (uses local Docker images)
- ClusterIP service (internal only)
- No health checks (FastMCP doesn't expose /health by default)

### Production Considerations

For production deployments:
1. Use a proper image registry (ECR, GCR, Docker Hub)
2. Change `imagePullPolicy` to `IfNotPresent` or `Always`
3. Add health check endpoints to main.py
4. Configure resource limits based on workload
5. Set up proper API key management (Vault, Secrets Manager)
6. Enable horizontal pod autoscaling for high load

## Troubleshooting

### Pod CrashLoopBackOff

```bash
# Check logs
kubectl logs -l app=ubo-pdf-tools --tail=100

# Common issues:
# - Missing dependencies: Rebuild image with --no-cache
# - Import errors: Verify pyproject.toml packages are installed
# - API key issues: Check environment variables
```

### MCPServer Not Available

```bash
# Check MCPServer status
kubectl get mcpserver ubo-pdf-tools-server -o yaml

# Verify service connectivity
kubectl get svc ubo-pdf-tools
kubectl port-forward svc/ubo-pdf-tools 8080:8080
curl http://localhost:8080/mcp
```

### Tool Discovery Fails

```bash
# Check if tools are registered
kubectl logs -l app=ubo-pdf-tools | grep "ListToolsRequest"

# Verify MCP endpoint
kubectl exec -it <pod-name> -- curl localhost:8080/mcp
```

## Architecture Details

### Pipeline Flow

1. **PDF Parsing**: PyMuPDF extracts text from PDF pages
2. **Chunking**: Recursive text splitting with 1000 char chunks, 300 char overlap
3. **Indexing**: ChromaDB vector store with OpenAI embeddings
4. **Retrieval**: Union retrieval strategy for ownership-relevant chunks
5. **Extraction**: LLM-based structured extraction (OpenAI/Anthropic)
6. **Validation**: Self-loop, voting-only, subsidiary filtering
7. **Normalization**: Entity deduplication and company reference resolution
8. **UBO Computation**: Graph traversal for effective ownership calculation

### Data Models

- **Entity**: `{id, name, type}` (COMPANY, PERSON, TRUST, OTHER)
- **OwnershipEdge**: `{owner_id, owned_id, pct, voting_pct, ownership_kind, evidence}`
- **Evidence**: `{doc_id, page, snippet}`

## Examples

See `examples/` directory for:
- `ubo-pdf-tools-agent.yaml`: Agent configuration
- `ubo-pdf-tools-query.yaml`: Example query

## License

Part of the ubo-resolver project. See project root for license details.
