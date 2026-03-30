# Changelog

## [0.2.0](https://github.com/mckinsey/agents-at-scale-marketplace/compare/executor-claude-agent-sdk-v0.1.1...executor-claude-agent-sdk-v0.2.0) (2026-03-30)


### ⚠ BREAKING CHANGES

* **executor-claude-agent-sdk:** Model configuration and API key now come from the Model CRD via `request.agent.model` instead of environment variables. The standalone `anthropic-api-key` K8s secret and `ANTHROPIC_MODEL` env var are no longer used.

#### Migration

1. Create a Model CRD with `provider: anthropic`:
   ```yaml
   apiVersion: ark.mckinsey.com/v1
   kind: Model
   metadata:
     name: claude-sonnet
   spec:
     model:
       value: claude-sonnet-4-20250514
     type: anthropic
     config:
       anthropic:
         apiKey:
           valueFrom:
             secretKeyRef:
               name: my-anthropic-secret
               key: api-key
   ```
2. Reference the Model from your Agent CRD: `spec.model.ref: claude-sonnet`
3. Remove the standalone `anthropic-api-key` K8s secret (no longer read by the executor)


### Features

* **executor-claude-agent-sdk:** read model config and API key from Model CRD instead of environment variables ([#model-crd-integration])


## [0.1.1](https://github.com/mckinsey/agents-at-scale-marketplace/compare/executor-claude-agent-sdk-v0.1.0...executor-claude-agent-sdk-v0.1.1) (2026-03-25)


### Features

* **executor-claude-agent-sdk:** add MCP server support ([#150](https://github.com/mckinsey/agents-at-scale-marketplace/issues/150)) ([39caf9e](https://github.com/mckinsey/agents-at-scale-marketplace/commit/39caf9e9aa25b67022d53e8d857b23955ff7a603))
* **executor-claude-agent-sdk:** add native Claude Agent SDK executor ([#146](https://github.com/mckinsey/agents-at-scale-marketplace/issues/146)) ([af4ac81](https://github.com/mckinsey/agents-at-scale-marketplace/commit/af4ac81fb6d78eda5dfafd2461c18c41ac580a8d))

## Changelog
