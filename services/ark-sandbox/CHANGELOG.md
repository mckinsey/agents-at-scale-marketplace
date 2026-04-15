# Changelog

All notable changes to ARK Sandbox will be documented in this file.

## [0.1.4](https://github.com/mckinsey/agents-at-scale-marketplace/compare/ark-sandbox-v0.1.3...ark-sandbox-v0.1.4) (2026-04-15)


### Bug Fixes

* Allow release-please to update all appVersion values ([#217](https://github.com/mckinsey/agents-at-scale-marketplace/issues/217)) ([f23d8e4](https://github.com/mckinsey/agents-at-scale-marketplace/commit/f23d8e4a0ebf728a4e91287d52e1e9ec89f45323))

## [0.1.3](https://github.com/mckinsey/agents-at-scale-marketplace/compare/ark-sandbox-v0.1.2...ark-sandbox-v0.1.3) (2026-04-14)


### Features

* marketplace install detection and url discovery ([#196](https://github.com/mckinsey/agents-at-scale-marketplace/issues/196)) ([b016ccf](https://github.com/mckinsey/agents-at-scale-marketplace/commit/b016ccf3203d5895ff7e70b40d349a66bf512bdf))

## [0.1.2](https://github.com/mckinsey/agents-at-scale-marketplace/compare/ark-sandbox-v0.1.1...ark-sandbox-v0.1.2) (2026-01-13)


### Bug Fixes

* add explicit MCP server path for Ark 0.1.50 compatibility ([#90](https://github.com/mckinsey/agents-at-scale-marketplace/issues/90)) ([c13f7e2](https://github.com/mckinsey/agents-at-scale-marketplace/commit/c13f7e23123bfafe1f95254f3615b7b80fef2690))

## [0.1.1](https://github.com/mckinsey/agents-at-scale-marketplace/compare/ark-sandbox-v0.1.0...ark-sandbox-v0.1.1) (2025-12-12)


### Features

* Ark Sandbox ([#83](https://github.com/mckinsey/agents-at-scale-marketplace/issues/83)) ([260097d](https://github.com/mckinsey/agents-at-scale-marketplace/commit/260097dfe024ac8721e2d950c27e7bb3ae3e8f60))

## [0.1.0] - 2025-12-05

### Added

- Initial release of ARK Sandbox
- Sandbox CRD for isolated container environments
- SandboxTemplate CRD for reusable configurations
- SandboxPool CRD for warm pool management
- MCP server with tools:
  - `create_sandbox` - Create new sandbox containers
  - `delete_sandbox` - Delete sandboxes
  - `execute_command` - Execute commands in sandboxes
  - `upload_file` - Upload files to sandboxes
  - `download_file` - Download files from sandboxes
  - `get_sandbox_logs` - Get sandbox logs
  - `list_sandboxes` - List all sandboxes
- Kopf-based Kubernetes controller for lifecycle management
- TTL-based automatic cleanup
- PVC mounting support for shared volumes
- HTTPRoute support for Gateway API
- MCPServer registration for ARK tool discovery
- Argo WorkflowTemplates for workflow integration
