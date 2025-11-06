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
    <a href="#services">Services</a>
  </p>
  <p align="center">
    <a href="https://github.com/mckinsey/agents-at-scale-marketplace/actions/workflows/main-push.yaml"><img src="https://github.com/mckinsey/agents-at-scale-marketplace/actions/workflows/main-push.yaml/badge.svg" alt="CI/CD"></a>
  </p>
</div>

---

A curated collection of services, agents, and tools for the Agents at Scale (ARK) platform, packaged as Helm charts with DevSpace support for seamless deployment and development.

> **Note on Versioning**: This repository uses a unified versioning strategy where all services share a common version number. Individual services do not maintain separate versions. When a release is created, the version is synchronized across all service charts and documentation.
## Services

| Service | Description | Chart |
|---------|-------------|-------|
| [`langfuse`](./services/langfuse) | Open-source LLM observability and analytics platform with session tracking | [Chart](./services/langfuse/chart) |
| [`phoenix`](./services/phoenix) | AI/ML observability and evaluation platform with OpenTelemetry integration | [Chart](./services/phoenix/chart) |

## Quick Start

### Deploy a Service

```bash
# Deploy using Helm from local chart
cd services/phoenix
helm dependency update chart/
helm install phoenix ./chart -n phoenix --create-namespace

# Or deploy with DevSpace for development
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
