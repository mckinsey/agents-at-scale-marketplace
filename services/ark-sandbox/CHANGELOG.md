# Changelog

All notable changes to ARK Sandbox will be documented in this file.

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

