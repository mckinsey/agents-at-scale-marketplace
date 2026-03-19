import logging
from typing import Dict, Any, Optional
from enum import Enum

logger = logging.getLogger(__name__)

try:
    from kubernetes import client as k8s_client
    K8S_AVAILABLE = True
except ImportError:
    K8S_AVAILABLE = False


class PricingAnnotations:
    INPUT_COST = "pricing.ark.mckinsey.com/input-cost"
    OUTPUT_COST = "pricing.ark.mckinsey.com/output-cost"
    CURRENCY = "pricing.ark.mckinsey.com/currency"
    UNIT = "pricing.ark.mckinsey.com/unit"


class PricingUnit(Enum):
    PER_MILLION_TOKENS = "per-million-tokens"
    PER_THOUSAND_TOKENS = "per-thousand-tokens"
    PER_HUNDRED_TOKENS = "per-hundred-tokens"


class MetricsCalculator:
    def __init__(self, parameters: Dict[str, Any]):
        self.parameters = parameters
        self.model_pricing = {
            "gpt-4": {"input": 0.03, "output": 0.06},
            "gpt-4-turbo": {"input": 0.01, "output": 0.03},
            "gpt-4o": {"input": 0.005, "output": 0.015},
            "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
            "gpt-3.5-turbo": {"input": 0.0015, "output": 0.002},
            "claude-3-sonnet": {"input": 0.003, "output": 0.015},
            "claude-3-haiku": {"input": 0.00025, "output": 0.00125}
        }

    async def calculate_overall_score(self, metrics: Dict[str, Any]) -> float:
        try:
            token_score = self._calculate_token_score(metrics)
            cost_score = self._calculate_cost_score(metrics)
            performance_score = self._calculate_performance_score(metrics)

            weights = self._get_score_weights()

            overall_score = (
                token_score * weights["token"] +
                cost_score * weights["cost"] +
                performance_score * weights["performance"]
            )

            self._update_metrics_with_scores(metrics, {
                "tokenScore": token_score,
                "costScore": cost_score,
                "performanceScore": performance_score
            })

            return overall_score

        except Exception as e:
            logger.error(f"Failed to calculate overall score: {e}")
            return 0.0

    def _calculate_token_score(self, metrics: Dict[str, Any]) -> float:
        try:
            total_tokens = metrics.get("totalTokens", 0)
            max_tokens = self._get_threshold("maxTokens", 5000)

            if total_tokens == 0:
                return 1.0

            if total_tokens > max_tokens:
                metrics.setdefault("threshold_violations", []).append("maxTokens")
                return max(0.1, 1.0 - (total_tokens - max_tokens) / max_tokens)

            score = 1.0 - (total_tokens / max_tokens)
            metrics.setdefault("passed_thresholds", []).append("maxTokens")

            token_efficiency = metrics.get("tokenEfficiency", 0)
            efficiency_threshold = self._get_threshold("tokenEfficiencyThreshold", 0.3)
            if token_efficiency >= efficiency_threshold:
                score = min(1.0, score + 0.1)
                metrics.setdefault("passed_thresholds", []).append("tokenEfficiency")

            return max(0.0, min(1.0, score))

        except Exception as e:
            logger.warning(f"Failed to calculate token score: {e}")
            return 0.5

    def _calculate_cost_score(self, metrics: Dict[str, Any]) -> float:
        try:
            if "totalCost" not in metrics:
                self._calculate_query_cost(metrics)

            total_cost = metrics.get("totalCost", 0)
            max_cost = self._get_threshold("maxCostPerQuery", 0.10)

            if total_cost == 0:
                return 1.0

            if total_cost > max_cost:
                metrics.setdefault("threshold_violations", []).append("maxCostPerQuery")
                return max(0.1, 1.0 - (total_cost - max_cost) / max_cost)

            score = 1.0 - (total_cost / max_cost)
            metrics.setdefault("passed_thresholds", []).append("maxCostPerQuery")

            return max(0.0, min(1.0, score))

        except Exception as e:
            logger.warning(f"Failed to calculate cost score: {e}")
            return 0.5

    def _calculate_performance_score(self, metrics: Dict[str, Any]) -> float:
        try:
            score = 1.0

            duration_seconds = metrics.get("executionDurationSeconds", 0)
            max_duration = self._parse_duration(self._get_threshold("maxDuration", "30s"))

            if duration_seconds > 0:
                if duration_seconds > max_duration:
                    metrics.setdefault("threshold_violations", []).append("maxDuration")
                    score *= max(0.1, 1.0 - ((duration_seconds - max_duration) / max_duration))
                else:
                    metrics.setdefault("passed_thresholds", []).append("maxDuration")
                    if duration_seconds < max_duration * 0.5:
                        score = min(1.0, score + 0.1)

            return max(0.0, min(1.0, score))

        except Exception as e:
            logger.warning(f"Failed to calculate performance score: {e}")
            return 0.5

    def _calculate_query_cost(self, metrics: Dict[str, Any]) -> None:
        try:
            total_tokens = metrics.get("totalTokens", 0)
            prompt_tokens = metrics.get("promptTokens", 0)
            completion_tokens = metrics.get("completionTokens", 0)
            model_name = metrics.get("modelName", "gpt-4")

            if total_tokens == 0:
                metrics["totalCost"] = 0.0
                return

            pricing = self._get_model_pricing(model_name)

            input_cost = (prompt_tokens / 1000) * pricing["input"]
            output_cost = (completion_tokens / 1000) * pricing["output"]
            total_cost = input_cost + output_cost

            metrics.update({
                "totalCost": round(total_cost, 4),
                "inputCost": round(input_cost, 4),
                "outputCost": round(output_cost, 4),
                "costPerToken": round(total_cost / total_tokens, 6) if total_tokens > 0 else 0
            })

        except Exception as e:
            logger.warning(f"Failed to calculate query cost: {e}")
            metrics["totalCost"] = 0.0

    def _get_model_pricing(self, model_name: str) -> Dict[str, float]:
        if K8S_AVAILABLE:
            annotation_pricing = self._get_model_pricing_from_annotations(model_name)
            if annotation_pricing:
                return annotation_pricing

        clean_name = model_name.lower().strip()

        if clean_name in self.model_pricing:
            return self.model_pricing[clean_name]

        for model, pricing in self.model_pricing.items():
            if model in clean_name or clean_name in model:
                return pricing

        return self.model_pricing["gpt-4"]

    def _get_model_pricing_from_annotations(self, model_name: str) -> Optional[Dict[str, float]]:
        if not K8S_AVAILABLE:
            return None
        try:
            custom_api = k8s_client.CustomObjectsApi()
            for namespace in ["default", "ark-system"]:
                try:
                    model = custom_api.get_namespaced_custom_object(
                        group="ark.mckinsey.com",
                        version="v1alpha1",
                        namespace=namespace,
                        plural="models",
                        name=model_name
                    )
                    annotations = model.get('metadata', {}).get('annotations', {})
                    input_cost_str = annotations.get(PricingAnnotations.INPUT_COST)
                    output_cost_str = annotations.get(PricingAnnotations.OUTPUT_COST)
                    unit = annotations.get(PricingAnnotations.UNIT, PricingUnit.PER_MILLION_TOKENS.value)

                    if input_cost_str is not None and output_cost_str is not None:
                        input_cost = float(input_cost_str)
                        output_cost = float(output_cost_str)
                        if unit == PricingUnit.PER_MILLION_TOKENS.value:
                            input_cost = input_cost / 1000
                            output_cost = output_cost / 1000
                        elif unit == PricingUnit.PER_HUNDRED_TOKENS.value:
                            input_cost = input_cost * 10
                            output_cost = output_cost * 10
                        return {"input": input_cost, "output": output_cost}
                except Exception:
                    continue
            return None
        except Exception:
            return None

    def _get_score_weights(self) -> Dict[str, float]:
        return {
            "token": float(self.parameters.get("tokenWeight", 0.35)),
            "cost": float(self.parameters.get("costWeight", 0.35)),
            "performance": float(self.parameters.get("performanceWeight", 0.30))
        }

    def _get_threshold(self, param_name: str, default_value) -> Any:
        value = self.parameters.get(param_name, default_value)
        if isinstance(value, str) and isinstance(default_value, (int, float)):
            try:
                return type(default_value)(value)
            except ValueError:
                return default_value
        return value

    def _parse_duration(self, duration_str: str) -> float:
        if isinstance(duration_str, (int, float)):
            return float(duration_str)
        duration_str = str(duration_str).lower().strip()
        try:
            if duration_str.endswith('s'):
                return float(duration_str[:-1])
            elif duration_str.endswith('m'):
                return float(duration_str[:-1]) * 60
            elif duration_str.endswith('h'):
                return float(duration_str[:-1]) * 3600
            else:
                return float(duration_str)
        except ValueError:
            return 30.0

    def _update_metrics_with_scores(self, metrics: Dict[str, Any], scores: Dict[str, float]) -> None:
        metrics.update(scores)
        metrics.setdefault("threshold_violations", [])
        metrics.setdefault("passed_thresholds", [])
