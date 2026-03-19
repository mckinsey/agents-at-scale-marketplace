import pytest
from evaluator.types import (
    EvaluationType,
    EvaluationScope,
    EvaluationParameters,
    UnifiedEvaluationRequest,
    EvaluationConfig,
    EvaluationResponse,
    TokenUsage,
)


def test_evaluation_type_values():
    assert EvaluationType.DIRECT == "direct"
    assert EvaluationType.QUERY == "query"
    assert EvaluationType.BASELINE == "baseline"
    assert EvaluationType.BATCH == "batch"
    assert EvaluationType.EVENT == "event"


def test_evaluation_scope_values():
    assert EvaluationScope.RELEVANCE == "relevance"
    assert EvaluationScope.ALL == "all"


def test_evaluation_parameters_defaults():
    params = EvaluationParameters()
    assert params.scope == "all"
    assert params.min_score == 0.7
    assert params.temperature == 0.0


def test_evaluation_parameters_scope_validation():
    params = EvaluationParameters(scope="relevance,accuracy")
    assert params.scope == "relevance,accuracy"


def test_evaluation_parameters_invalid_scope():
    params = EvaluationParameters(scope="invalid_scope")
    assert params.scope == "all"


def test_evaluation_parameters_get_scope_list():
    params = EvaluationParameters(scope="relevance,accuracy")
    scope_list = params.get_scope_list()
    assert "relevance" in scope_list
    assert "accuracy" in scope_list


def test_evaluation_parameters_from_request_params():
    raw_params = {"scope": "relevance", "min-score": "0.8", "temperature": "0.5"}
    params = EvaluationParameters.from_request_params(raw_params)
    assert params.scope == "relevance"
    assert params.min_score == 0.8


def test_unified_evaluation_request():
    request = UnifiedEvaluationRequest(
        type=EvaluationType.DIRECT,
        config=EvaluationConfig(input="test input", output="test output"),
        parameters={"provider": "ark"}
    )
    assert request.type == EvaluationType.DIRECT
    assert request.config.input == "test input"


def test_evaluation_response():
    response = EvaluationResponse(
        score="0.85",
        passed=True,
        metadata={"reasoning": "Good"},
        tokenUsage=TokenUsage(promptTokens=100, completionTokens=50, totalTokens=150)
    )
    assert response.score == "0.85"
    assert response.passed is True
    assert response.tokenUsage.totalTokens == 150


def test_token_usage_defaults():
    usage = TokenUsage()
    assert usage.promptTokens == 0
    assert usage.completionTokens == 0
    assert usage.totalTokens == 0
