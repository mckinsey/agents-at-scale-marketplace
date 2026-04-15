# Changelog

## [0.1.6](https://github.com/mckinsey/agents-at-scale-marketplace/compare/executor-claude-agent-sdk-v0.1.5...executor-claude-agent-sdk-v0.1.6) (2026-04-15)


### Bug Fixes

* annotation added ([#214](https://github.com/mckinsey/agents-at-scale-marketplace/issues/214)) ([a963fc2](https://github.com/mckinsey/agents-at-scale-marketplace/commit/a963fc2ecb7459b7108b467b7fb69b40411233d0))

## [0.1.5](https://github.com/mckinsey/agents-at-scale-marketplace/compare/executor-claude-agent-sdk-v0.1.4...executor-claude-agent-sdk-v0.1.5) (2026-04-03)


### Bug Fixes

* **executors/claude-agent-sdk:** pin dependencies via uv.lock in Docker build ([#190](https://github.com/mckinsey/agents-at-scale-marketplace/issues/190)) ([5e130e0](https://github.com/mckinsey/agents-at-scale-marketplace/commit/5e130e0235ea5553a42c973a58d11a9c8795a170))

## [0.1.4](https://github.com/mckinsey/agents-at-scale-marketplace/compare/executor-claude-agent-sdk-v0.1.3...executor-claude-agent-sdk-v0.1.4) (2026-04-02)


### Bug Fixes

* **executors/claude-agent-sdk:** update model reference to claude-sonnet-4-6 ([#188](https://github.com/mckinsey/agents-at-scale-marketplace/issues/188)) ([b17021b](https://github.com/mckinsey/agents-at-scale-marketplace/commit/b17021bd4379a01baafe0e20b90a5b8b5b09d66e))

## [0.1.3](https://github.com/mckinsey/agents-at-scale-marketplace/compare/executor-claude-agent-sdk-v0.1.2...executor-claude-agent-sdk-v0.1.3) (2026-04-02)


### Bug Fixes

* replace local file:// helm refs with OCI registry and pin ark-sdk ([#182](https://github.com/mckinsey/agents-at-scale-marketplace/issues/182)) ([0b3a907](https://github.com/mckinsey/agents-at-scale-marketplace/commit/0b3a907b6118ce0655be024b1b34474a2334b498))

## [0.1.2](https://github.com/mckinsey/agents-at-scale-marketplace/compare/executor-claude-agent-sdk-v0.1.1...executor-claude-agent-sdk-v0.1.2) (2026-03-30)


### Features

* **executor-claude-agent-sdk:** read model config from Model CRD ([#158](https://github.com/mckinsey/agents-at-scale-marketplace/issues/158)) ([df75acb](https://github.com/mckinsey/agents-at-scale-marketplace/commit/df75acb09ef1b57226b38fc857db0c0d566ca697))

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
