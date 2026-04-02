<div align="center">
  <h1 align="center"><code>🏪📦🧰 Agents at Scale Marketplace</code></h1>
  <h4 align="center">Ready-to-Deploy Services for the Agents at Scale Ecosystem</h4>
  <p align="center">
    <strong>Helm Charts & DevSpace Configurations</strong>
  </p>
  <p align="center">
    <em>Deploy observability, monitoring, and agentic services to any Kubernetes cluster.</em>
  </p>

  <hr>

  <p align="center">
    <a href="#quick-start">Quick Start</a> •
    <a href="https://mckinsey.github.io/agents-at-scale-marketplace/">Documentation</a> •
    <a href="#services">Services</a> •
    <a href="https://github.com/mckinsey/agents-at-scale-ark"><strong>Ark Platform →</strong></a>
  </p>
  <p align="center">
    <a href="https://github.com/mckinsey/agents-at-scale-marketplace/actions/workflows/main-push.yaml"><img src="https://github.com/mckinsey/agents-at-scale-marketplace/actions/workflows/main-push.yaml/badge.svg" alt="CI/CD"></a>
  </p>
</div>

---

> **Part of the [Agents at Scale (Ark)](https://github.com/mckinsey/agents-at-scale-ark) Platform**
> A curated collection of services, agents, and tools packaged as Helm charts with DevSpace support for seamless deployment and development.

## Executors

External execution engines that process agent workloads. Implement `BaseExecutor` from `ark-sdk` and communicate via A2A protocol.

| Executor                                                  | Description                                                  | Chart                                          |
| --------------------------------------------------------- | ------------------------------------------------------------ | ---------------------------------------------- |
| [`claude-agent-sdk`](./executors/claude-agent-sdk)        | Native Claude executor with built-in tools and session persistence | [Chart](./executors/claude-agent-sdk/chart) |
| [`langchain`](./executors/langchain)                      | LangChain executor with RAG support                          | [Chart](./executors/langchain/chart)           |

## Services

Infrastructure add-ons deployed alongside the [Ark platform](https://github.com/mckinsey/agents-at-scale-ark).

| Service                                       | Description                                                                | Chart                                      |
| --------------------------------------------- | -------------------------------------------------------------------------- | ------------------------------------------ |
| [`a2a-inspector`](./services/a2a-inspector)   | Developer tool for testing and debugging A2A protocol agents               | [Chart](./services/a2a-inspector/chart)    |
| [`ark-sandbox`](./services/ark-sandbox)       | Isolated container environments for AI agent code execution with MCP tools | [Chart](./services/ark-sandbox/chart)      |
| [`file-gateway`](./services/file-gateway)     | S3-compatible file storage gateway with REST API for shared storage access | [Chart](./services/file-gateway/chart)     |
| [`langfuse`](./services/langfuse)             | Open-source LLM observability and analytics platform with session tracking | [Chart](./services/langfuse/chart)         |
| [`mcp-inspector`](./services/mcp-inspector)   | Developer tool for testing and debugging MCP servers                       | [Chart](./services/mcp-inspector/chart)    |
| [`phoenix`](./services/phoenix)               | AI/ML observability and evaluation platform with OpenTelemetry integration | [Chart](./services/phoenix/chart)          |

## Agents

Pre-built agents that can be deployed to your Ark cluster.

| Agent                     | Description                                                         | Chart                        |
| ------------------------- | ------------------------------------------------------------------- | ---------------------------- |
| [`noah`](./agents/noah)   | Runtime administration agent with cluster privileges and MCP server | [Chart](./agents/noah/chart) |

## MCP Servers

Tool providers registered as `MCPServer` CRDs. Agents reference individual tools in their spec.

| MCP Server                                                       | Description                                                            | Chart                                             |
| ---------------------------------------------------------------- | ---------------------------------------------------------------------- | ------------------------------------------------- |
| [`filesystem-mcp-server`](./mcps/filesystem-mcp-server)         | Filesystem operations with session management and workspace config     | [Chart](./mcps/filesystem-mcp-server/chart)       |
| [`speech-mcp-server`](./mcps/speech-mcp-server)                 | Audio transcription via OpenAI Whisper                                 | [Chart](./mcps/speech-mcp-server/chart)           |
| [`pdf-extraction-mcp`](./mcps/pdf-extraction-mcp)               | PDF ownership extraction with LLM analysis                             | [Chart](./mcps/pdf-extraction-mcp/chart)          |
| [`web-research-mcp`](./mcps/web-research-mcp)                   | Web research via Tavily or Perplexity                                  | [Chart](./mcps/web-research-mcp/chart)            |
| [`perplexity-ask-mcp`](./mcps/perplexity-ask-mcp)               | Conversational AI with real-time web search via Perplexity API         | [Chart](./mcps/perplexity-ask-mcp/chart)          |
| [`companies-house-mcp`](./mcps/companies-house-mcp)             | UK Companies House API for company search and beneficial ownership     | [Chart](./mcps/companies-house-mcp/chart)         |

## Quick Start

### Install with Ark CLI (Recommended)

The easiest way to install marketplace items is using the [Ark CLI](https://mckinsey.github.io/agents-at-scale-ark/):

```bash
# Executors
ark install marketplace/executors/executor-claude-agent-sdk
ark install marketplace/executors/executor-langchain

# Services
ark install marketplace/services/phoenix
ark install marketplace/services/langfuse
ark install marketplace/services/ark-sandbox
ark install marketplace/services/file-gateway
ark install marketplace/services/a2a-inspector
ark install marketplace/services/mcp-inspector

# Agents
ark install marketplace/agents/noah
```

### Deploy with Helm

For production deployments or custom configurations:

```bash
# Deploy using Helm from local chart
cd services/phoenix
helm dependency update chart/
helm install phoenix ./chart -n phoenix --create-namespace
```

### Deploy with DevSpace

For local development with hot-reload:

```bash
cd services/phoenix
devspace deploy
```

### Development Mode

```bash
# Use DevSpace for local development with hot-reload and port-forwarding
cd services/phoenix
devspace dev

# This will:
# - Deploy Phoenix to your cluster
# - Set up port-forwarding to access the dashboard
# - Watch for changes and auto-reload
```

### Uninstall a Service

```bash
# Using Helm
helm uninstall phoenix -n phoenix

# Using DevSpace
cd services/phoenix
devspace purge
```

## Documentation

Detailed documentation for marketplace services can be found in the [`docs/`](./docs) directory.

## Contributing

1. Choose the appropriate directory (`executors/`, `services/`, `mcps/`, `agents/`, `demos/`)
2. Each component needs: Helm chart in `chart/`, `README.md`, `devspace.yaml`
3. Add an entry to `marketplace.json`
4. Test locally with DevSpace or Helm
5. Submit a pull request with a conventional commit title

See [CONTRIBUTING.md](./CONTRIBUTING.md) for full guidelines.

## Related Projects

- **[Ark (Agents at Scale)](https://github.com/mckinsey/agents-at-scale-ark)** — The core platform
- **[Ark Documentation](https://mckinsey.github.io/agents-at-scale-ark/)** — Platform documentation

## License

See [LICENSE](./LICENSE) for more information.
