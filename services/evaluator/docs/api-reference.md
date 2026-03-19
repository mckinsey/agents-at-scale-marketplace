# API Reference

## Endpoints

### POST /evaluate

Unified LLM-as-a-Judge evaluation endpoint.

**Request:**
```json
{
  "type": "direct|query|baseline|batch|event",
  "config": {},
  "parameters": {},
  "evaluatorName": "optional-name"
}
```

**Response:**
```json
{
  "score": "0.85",
  "passed": true,
  "metadata": {
    "provider": "ark",
    "evaluation_criteria": {"relevance": 0.9, "accuracy": 0.8}
  },
  "error": null,
  "tokenUsage": {"promptTokens": 150, "completionTokens": 80, "totalTokens": 230}
}
```

#### Direct Evaluation

```json
{
  "type": "direct",
  "config": {
    "input": "What is machine learning?",
    "output": "Machine learning is a subset of AI..."
  },
  "parameters": {
    "provider": "ark",
    "scope": "all",
    "threshold": "0.8"
  }
}
```

#### Query Evaluation (requires Ark operator)

```json
{
  "type": "query",
  "config": {
    "queryRef": {"name": "my-query", "namespace": "default"}
  },
  "parameters": {
    "provider": "ark",
    "scope": "relevance,accuracy"
  }
}
```

### POST /evaluate-metrics

Deterministic metrics evaluation without LLM calls.

**Request:** Same format as `/evaluate` with metrics-specific parameters.

**Response:** Same format with metric breakdown in metadata.

### GET /providers/{provider}/metrics

List available metrics for a provider.

**Providers:** `ark`, `ragas`, `langfuse`

### GET /providers/{provider}/metrics/{metric}

Get field requirements for a specific metric.

### GET /health

Returns `200 OK` when the service is running.

### GET /ready

Returns `200 OK` when the service is ready to accept requests.

## Error Codes

| Code | Description |
|------|-------------|
| 400 | Invalid request (missing fields, invalid type) |
| 404 | Provider or metric not found |
| 500 | Internal evaluation error |
| 501 | Batch type not supported (handled by operator) |
