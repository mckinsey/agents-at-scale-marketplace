import logging
from typing import Dict, Any
from ..types import (
    EvaluationResponse, QueryRef,
)
from .metric_types import DirectRequest, QueryRefRequest
from .ark_client import ArkClient
from .metrics import MetricsCalculator

logger = logging.getLogger(__name__)


class MetricEvaluator:
    def __init__(self, parameters: Dict[str, Any]):
        self.parameters = parameters
        self.ark_client = ArkClient()
        self.metrics_calculator = MetricsCalculator(parameters)

    async def evaluate_direct(self, request: DirectRequest) -> EvaluationResponse:
        try:
            synthetic_metrics = self._create_synthetic_metrics_from_direct(request)
            overall_score = await self.metrics_calculator.calculate_overall_score(synthetic_metrics)
            passed = self._determine_pass_status(overall_score, synthetic_metrics)
            metadata = self._build_unified_metadata(synthetic_metrics, overall_score)

            return EvaluationResponse(
                score=f"{overall_score:.2f}",
                passed=passed,
                metadata=metadata
            )

        except Exception as e:
            logger.error(f"Direct evaluation failed: {e}")
            return EvaluationResponse(score="0.0", passed=False, error=str(e))

    async def evaluate_query_ref(self, request: QueryRefRequest) -> EvaluationResponse:
        try:
            query_ref = request.queryRef
            query_config = await self.ark_client.load_query(query_ref)
            metrics = await self.ark_client.extract_metrics(query_config)
            overall_score = await self.metrics_calculator.calculate_overall_score(metrics)
            passed = self._determine_pass_status(overall_score, metrics)
            metadata = self._build_unified_metadata(metrics, overall_score)

            return EvaluationResponse(
                score=f"{overall_score:.2f}",
                passed=passed,
                metadata=metadata
            )

        except Exception as e:
            logger.error(f"Query-ref evaluation failed: {e}")
            return EvaluationResponse(score="0.0", passed=False, error=str(e))

    def _determine_pass_status(self, overall_score: float, metrics: Dict[str, Any]) -> bool:
        min_score = float(self.parameters.get("minScore", 0.7))
        if overall_score < min_score:
            return False

        threshold_violations = metrics.get("threshold_violations", [])
        critical_violations = ["maxTokens", "maxCostPerQuery", "maxDuration"]
        for violation in threshold_violations:
            if violation in critical_violations:
                return False
        return True

    def _create_synthetic_metrics_from_direct(self, request: DirectRequest) -> Dict[str, Any]:
        input_length = len(request.input) if request.input else 0
        output_length = len(request.output) if request.output else 0

        estimated_prompt_tokens = input_length // 4
        estimated_completion_tokens = output_length // 4
        estimated_total_tokens = estimated_prompt_tokens + estimated_completion_tokens

        metrics = {
            "totalTokens": estimated_total_tokens,
            "promptTokens": estimated_prompt_tokens,
            "completionTokens": estimated_completion_tokens,
            "totalResponseLength": output_length,
            "responseCount": 1,
            "averageResponseLength": output_length,
            "isCompleted": True,
            "hasErrors": False,
            "queryPhase": "direct-evaluation",
            "responseCompleteness": min(1.0, output_length / 50) if output_length > 0 else 0
        }

        if estimated_prompt_tokens > 0:
            metrics["tokenEfficiency"] = estimated_completion_tokens / estimated_prompt_tokens
        else:
            metrics["tokenEfficiency"] = 0

        return metrics

    def _build_unified_metadata(self, metrics: Dict[str, Any], overall_score: float) -> Dict[str, str]:
        threshold_violations = metrics.get("threshold_violations", [])

        if threshold_violations:
            reasoning = f"Performance metrics evaluation failed due to threshold violations: {', '.join(threshold_violations)}"
        elif overall_score >= 0.8:
            reasoning = "All performance metrics within acceptable thresholds with excellent scores"
        elif overall_score >= 0.6:
            reasoning = "All performance metrics within acceptable thresholds with good scores"
        else:
            reasoning = "Performance metrics within thresholds but could be improved"

        metadata = {
            "reasoning": reasoning,
            "evaluation_type": "performance_metrics",
            "total_tokens": str(metrics.get("totalTokens", 0)),
            "execution_time": metrics.get("executionDuration", "unknown"),
            "cost": str(metrics.get("totalCost", 0.0))
        }

        if "tokenScore" in metrics:
            metadata["token_score"] = f"{metrics['tokenScore']:.2f}"
        if "costScore" in metrics:
            metadata["cost_score"] = f"{metrics['costScore']:.2f}"
        if "performanceScore" in metrics:
            metadata["performance_score"] = f"{metrics['performanceScore']:.2f}"

        return metadata
