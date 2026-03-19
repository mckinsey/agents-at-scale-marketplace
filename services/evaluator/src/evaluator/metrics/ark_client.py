import logging
from typing import Dict, Any
from ..types import QueryRef
from .query_resolver import QueryResolver

logger = logging.getLogger(__name__)


class ArkClient:
    def __init__(self):
        self.query_resolver = QueryResolver()

    async def load_query(self, query_ref: QueryRef):
        try:
            query_config = await self.query_resolver.resolve_query(query_ref)
            return query_config
        except Exception as e:
            logger.error(f"Failed to load query {query_ref.name}: {e}")
            raise

    async def extract_metrics(self, query_config) -> Dict[str, Any]:
        try:
            metrics = self.query_resolver.extract_metrics_from_query(query_config)
            self._add_derived_metrics(metrics)
            return metrics
        except Exception as e:
            logger.error(f"Failed to extract metrics: {e}")
            raise

    def _add_derived_metrics(self, metrics: Dict[str, Any]) -> None:
        import time
        metrics["evaluationTimestamp"] = time.time()
        metrics["threshold_violations"] = []
        metrics["passed_thresholds"] = []

        if "totalTokens" in metrics:
            metrics["estimatedCost"] = metrics["totalTokens"] * 0.00002
