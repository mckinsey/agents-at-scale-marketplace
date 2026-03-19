import pytest
from evaluator.metrics.metrics import MetricsCalculator


@pytest.mark.asyncio
async def test_calculate_overall_score_empty_metrics():
    calc = MetricsCalculator({})
    metrics = {"totalTokens": 0}
    score = await calc.calculate_overall_score(metrics)
    assert 0.0 <= score <= 1.0


@pytest.mark.asyncio
async def test_calculate_overall_score_with_tokens():
    calc = MetricsCalculator({"maxTokens": "10000"})
    metrics = {
        "totalTokens": 1000,
        "promptTokens": 600,
        "completionTokens": 400,
        "tokenEfficiency": 0.67,
    }
    score = await calc.calculate_overall_score(metrics)
    assert 0.0 <= score <= 1.0
    assert "tokenScore" in metrics
    assert "costScore" in metrics
    assert "performanceScore" in metrics


@pytest.mark.asyncio
async def test_token_score_exceeds_threshold():
    calc = MetricsCalculator({"maxTokens": "100"})
    metrics = {"totalTokens": 500, "threshold_violations": [], "passed_thresholds": []}
    score = await calc.calculate_overall_score(metrics)
    assert "maxTokens" in metrics.get("threshold_violations", [])


def test_parse_duration():
    calc = MetricsCalculator({})
    assert calc._parse_duration("30s") == 30.0
    assert calc._parse_duration("2m") == 120.0
    assert calc._parse_duration("1h") == 3600.0
    assert calc._parse_duration(45) == 45.0


def test_get_score_weights_defaults():
    calc = MetricsCalculator({})
    weights = calc._get_score_weights()
    assert weights["token"] == 0.35
    assert weights["cost"] == 0.35
    assert weights["performance"] == 0.30


def test_get_score_weights_custom():
    calc = MetricsCalculator({"tokenWeight": "0.5", "costWeight": "0.3", "performanceWeight": "0.2"})
    weights = calc._get_score_weights()
    assert weights["token"] == 0.5
    assert weights["cost"] == 0.3
    assert weights["performance"] == 0.2
