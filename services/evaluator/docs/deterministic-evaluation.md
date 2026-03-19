# Deterministic Evaluation

Objective performance assessment without LLM calls via `POST /evaluate-metrics`.

## Scoring Dimensions

### Token Score (weight: 0.3)

Measures token efficiency relative to `maxTokens` threshold.

### Cost Score (weight: 0.3)

Per-query cost relative to `maxCostPerQuery` threshold.

### Performance Score (weight: 0.2)

Latency and throughput compared to `maxDuration` and `minTokensPerSecond`.

### Quality Score (weight: 0.2)

Response completeness and length within `minResponseLength` / `maxResponseLength` bounds.

## Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `maxTokens` | `5000` | Max total tokens allowed |
| `maxDuration` | `30s` | Max execution time |
| `maxCostPerQuery` | `0.10` | Max cost per query (USD) |
| `minTokensPerSecond` | `10.0` | Min throughput |
| `tokenWeight` | `0.3` | Weight for token score |
| `costWeight` | `0.3` | Weight for cost score |
| `performanceWeight` | `0.2` | Weight for performance score |
| `qualityWeight` | `0.2` | Weight for quality score |
| `responseCompletenessThreshold` | `0.8` | Min response completeness |
| `minResponseLength` | `50` | Min response chars |
| `maxResponseLength` | `2000` | Max response chars |
| `tokenEfficiencyThreshold` | `0.3` | Min token efficiency |
| `costEfficiencyThreshold` | `0.8` | Min cost efficiency |

## Example

```bash
curl -s -X POST http://localhost:8000/evaluate-metrics \
  -H "Content-Type: application/json" \
  -d '{
    "type": "direct",
    "config": {"input": "test", "output": "response"},
    "parameters": {"maxTokens": "1000", "maxCostPerQuery": "0.05"}
  }'
```
