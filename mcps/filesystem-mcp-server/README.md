# MCP Filesystem Server with Session Management

> **⚠️ Deprecated.** This standalone MCP server is deprecated and will be combined into
> the [file-gateway](../../services/file-gateway) service. New deployments should use
> file-gateway, which bundles this MCP alongside the REST file-api and VersityGW and
> supports both the `filesystem` (PVC) and `s3` storage backends. This standalone chart
> remains for now but will be removed in a future release.

MCP-compliant filesystem server with persistent session tracking and annotation-driven workspace configuration.

## Quick Start

```bash
# Deploy with Helm (uses the published image from ghcr.io)
helm install mcp-filesystem ./chart -n default --create-namespace

# Verify
kubectl get mcpserver filesystem-mcp-server
kubectl get pods -l app.kubernetes.io/name=filesystem-mcp-server
```

The chart creates its own 10Gi PVC by default. To share file-gateway's storage instead, set `persistence.existingClaim=file-gateway-storage` (and `podSecurityContext.runAsUser=1000`, `fsGroup=1000` to match VersityGW's file ownership — see comments in `chart/values.yaml`).

### Local development

```bash
# Build a local image
docker build -t filesystem-mcp-server:latest .

# Install with the local image
helm install mcp-filesystem ./chart \
  --set image.repository=filesystem-mcp-server \
  --set image.tag=latest \
  --set image.pullPolicy=IfNotPresent
```

## Features

- **MCP Protocol Compliant**: Full implementation of MCP session lifecycle
- **Persistent Session Tracking**: Session metadata survives server restarts via file-based storage
- **LRU Eviction**: Automatically evicts least recently used sessions when limit reached
- **Annotation-Driven Configuration**: Workspaces configured via Ark query annotations
- **Shared Base Directory**: All operations under `/data/` with user-specified workspaces
- **All Filesystem Operations**: Read, write, edit, move, search, list, tree

## Configuration

Environment variables (configured in `chart/values.yaml`):
- `PORT`: Server port (default: 8080)
- `STORAGE_BACKEND`: Storage adapter, `filesystem` (default) or `s3`
- `BASE_DATA_DIR`: Base directory for all filesystem operations, `filesystem` backend (default: /data)
- `SESSION_FILE`: Path to session metadata storage (default: /data/sessions/sessions.json)
- `MAX_SESSIONS`: Maximum concurrent sessions (default: 1000)

### Storage backends

The server selects a storage adapter at startup via `STORAGE_BACKEND`. Both adapters
expose the identical MCP tool set, so consumers are unaffected by the choice.

- `filesystem` (default) — local disk under `BASE_DATA_DIR` (PVC-backed).
- `s3` — an S3 bucket via `@aws-sdk/client-s3` (objects keyed by path; "directories"
  are key prefixes). Used by the `file-gateway` service when VersityGW runs its `s3`
  backend, so the MCP and file-api share one bucket. Extra env vars: `AWS_ENDPOINT_URL`,
  `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` (`AWS_SESSION_TOKEN` honoured),
  `AWS_REGION`, `BUCKET_NAME`, and optional `S3_KEY_PREFIX` (defaults to the bucket root).

Helm chart options:
- `persistence.size`: Storage size for persistent volume (default: 10Gi)
- `persistence.storageClass`: Storage class for PVC
- `resources`: CPU and memory limits/requests

## Workspace Configuration

Workspaces are configured via Ark query annotations using the `set_base_directory` tool:

```yaml
apiVersion: ark.mckinsey.com/v1alpha1
kind: Query
metadata:
  name: my-query
  annotations:
    "ark.mckinsey.com/mcp-server-settings": |
      {"default/mcp-filesystem": {
        "toolCalls": [{
          "name": "set_base_directory",
          "arguments": {"path": "my-workspace"}
        }]
      }}
spec:
  input: "List all files"
  targets:
    - name: filesystem-agent
```

This creates and configures `/data/my-workspace/` as the working directory for all filesystem operations in that query.

## Using with Ark

The MCP server creates an `MCPServer` resource that auto-generates tools with the `mcp-filesystem-` prefix.

Example agent configuration:

```yaml
apiVersion: ark.mckinsey.com/v1alpha1
kind: Agent
metadata:
  name: filesystem
spec:
  tools:
    - name: mcp-filesystem-read-file
      type: custom
    - name: mcp-filesystem-write-file
      type: custom
    - name: mcp-filesystem-edit-file
      type: custom
    - name: mcp-filesystem-create-directory
      type: custom
    - name: mcp-filesystem-list-directory
      type: custom
```

See `samples/agents/filesystem.yaml` for complete configuration.

Example query:

```bash
ark query agent/filesystem "Create a file hello.txt with content 'Hello World', then list all files"
```

For detailed usage examples and session management, see `docs/content/user-guide/samples/mcp-servers.mdx`.

## Architecture

**Clean separation of concerns:**

### Session Wrapper (`src/index.ts`)
- MCP protocol session lifecycle (ID generation, tracking)
- Session metadata persistence (sessions.json)
- LRU eviction and cleanup
- Transport management
- **Generic and reusable** - can be copied to other MCP servers

### Filesystem Adapter (`src/adapters/filesystem/`)
- MCP tool definitions and implementations
- File operations (read, write, edit, search, list, tree)
- Path validation and security
- Workspace management via `set_base_directory`

### Key Design Principles
- **MCP sessions ≠ application state**: Sessions track connections, not configuration
- **Annotations as source of truth**: Workspace configuration comes from Ark annotations
- **Single base directory**: All sessions share `/data/` with user-specified subdirectories
- **No per-session directories**: Workspaces are explicitly named and persistent