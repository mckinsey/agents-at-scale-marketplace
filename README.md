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
    <a href="https://github.com/mckinsey/agents-at-scale-ark"><strong>ARK Platform →</strong></a>
  </p>
  <p align="center">
    <a href="https://github.com/mckinsey/agents-at-scale-marketplace/actions/workflows/main-push.yaml"><img src="https://github.com/mckinsey/agents-at-scale-marketplace/actions/workflows/main-push.yaml/badge.svg" alt="CI/CD"></a>
  </p>
</div>

---

> **Part of the [Agents at Scale (ARK)](https://github.com/mckinsey/agents-at-scale-ark) Platform**  
> A curated collection of services, agents, and tools packaged as Helm charts with DevSpace support for seamless deployment and development.

## Services

Services are designed to integrate seamlessly with the [ARK platform](https://github.com/mckinsey/agents-at-scale-ark) and can be deployed to any Kubernetes cluster.

| Service                                       | Description                                                                | Chart                                      |
| --------------------------------------------- | -------------------------------------------------------------------------- | ------------------------------------------ |
| [`a2a-inspector`](./services/a2a-inspector)   | Developer tool for testing and debugging A2A protocol agents               | [Chart](./services/a2a-inspector/chart)    |
| [`ark-sandbox`](./services/ark-sandbox)       | Isolated container environments for AI agent code execution with MCP tools | [Chart](./services/ark-sandbox/chart)      |
| [`file-gateway`](./services/file-gateway)     | S3-compatible file storage gateway with REST API for shared storage access | [Chart](./services/file-gateway/chart)     |
| [`langfuse`](./services/langfuse)             | Open-source LLM observability and analytics platform with session tracking | [Chart](./services/langfuse/chart)         |
| [`mcp-inspector`](./services/mcp-inspector)   | Developer tool for testing and debugging MCP servers                       | [Chart](./services/mcp-inspector/chart)    |
| [`phoenix`](./services/phoenix)               | AI/ML observability and evaluation platform with OpenTelemetry integration | [Chart](./services/phoenix/chart)          |

## Agents

Pre-built agents that can be deployed to your ARK cluster for various operational tasks.

| Agent                     | Description                                                         | Chart                        |
| ------------------------- | ------------------------------------------------------------------- | ---------------------------- |
| [`noah`](./agents/noah)   | Runtime administration agent with cluster privileges and MCP server | [Chart](./agents/noah/chart) |

## Quick Start

### Install with ARK CLI (Recommended)

The easiest way to install marketplace services and agents is using the [ARK CLI](https://mckinsey.github.io/agents-at-scale-ark/):

```bash
# Install services
ark install marketplace/services/a2a-inspector
ark install marketplace/services/ark-sandbox
ark install marketplace/services/file-gateway
ark install marketplace/services/langfuse
ark install marketplace/services/mcp-inspector
ark install marketplace/services/phoenix

# Install agents
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

1. Make changes to services in `./services/`
2. Ensure your service includes:
   - Helm chart in `chart/` directory
   - `README.md` with service documentation
   - `devspace.yaml` for local development
3. Test locally using DevSpace or Helm
4. Submit a pull request

## Future Plans

This marketplace will include:

- Additional observability services
- Pre-built agents and agent templates
- Reusable tools and utilities

## Related Projects

- **[ARK (Agents at Scale)](https://github.com/mckinsey/agents-at-scale-ark)** - The main platform repository
- **[ARK Documentation](https://mckinsey.github.io/agents-at-scale-ark/)** - Complete platform documentation

## License

See [LICENSE](./LICENSE) for more information.
