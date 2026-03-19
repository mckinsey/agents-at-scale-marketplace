# Configuration

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `HOST` | `0.0.0.0` | Server bind address |
| `PORT` | `8000` | Server port |
| `WORKERS` | `4` | Uvicorn worker count |
| `DEFAULT_MODEL_ENDPOINT` | - | LLM endpoint URL |
| `DEFAULT_MODEL_API_KEY` | - | LLM API key |
| `DEFAULT_MODEL_NAME` | `gpt-4o-mini` | Default model name |
| `DEFAULT_MODEL_TYPE` | `openai` | Model type (`openai`, `azure`, `ark`) |
| `KUBERNETES_INTEGRATION` | `true` | Enable K8s-dependent features |

## Helm Values

### Application

```yaml
app:
  name: evaluator
  image:
    repository: ghcr.io/mckinsey/agents-at-scale-marketplace/evaluator
    pullPolicy: IfNotPresent
  env:
    - name: HOST
      value: "0.0.0.0"
    - name: PORT
      value: "8000"
    - name: WORKERS
      value: "4"
  resources:
    requests:
      memory: "512Mi"
      cpu: "250m"
    limits:
      memory: "1Gi"
      cpu: "1000m"
```

### Service

```yaml
service:
  name: evaluator
  type: ClusterIP
  port: 8000
  targetPort: 8000
```

### Evaluator CRD Registration

```yaml
evaluatorCRD:
  enabled: true
  description: "Marketplace evaluator service"
```

Set `enabled: false` when running without the Ark operator.

### HTTPRoute

```yaml
httpRoute:
  enabled: false
  parentRefs:
    - name: localhost-gateway
      namespace: ark-system
  hostnames:
    - "evaluator.default.127.0.0.1.nip.io"
```

## LLM Evaluation Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `threshold` | `0.7` | Minimum passing score |
| `scope` | `all` | Criteria to evaluate (`relevance,accuracy,clarity,...`) |
| `temperature` | `0.1` | LLM temperature |
| `max_tokens` | `500` | Max tokens for evaluation response |
| `debug` | `false` | Enable debug logging |

## RAGAS Provider

Azure: `azure.api_key`, `azure.endpoint`, `azure.api_version`, `azure.deployment_name`, `azure.embedding_deployment`

OpenAI: `openai.api_key`, `openai.base_url`, `openai.model`, `openai.embedding_model`

## Langfuse Provider

`langfuse.host`, `langfuse.public_key`, `langfuse.secret_key`, `langfuse.azure_api_key`, `langfuse.azure_endpoint`, `langfuse.azure_deployment`, `langfuse.model_version`
