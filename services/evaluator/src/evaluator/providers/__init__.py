import logging

from .factory import EvaluationProviderFactory
from .direct_evaluation import DirectEvaluationProvider
from .baseline_evaluation import BaselineEvaluationProvider
from .batch_evaluation import BatchEvaluationProvider

logger = logging.getLogger(__name__)

EvaluationProviderFactory.register("direct", DirectEvaluationProvider)
EvaluationProviderFactory.register("baseline", BaselineEvaluationProvider)
EvaluationProviderFactory.register("batch", BatchEvaluationProvider)

try:
    from .query_evaluation import QueryEvaluationProvider
    EvaluationProviderFactory.register("query", QueryEvaluationProvider)
except ImportError:
    logger.info("Query evaluation provider not available (kubernetes package not installed)")

try:
    from .event_evaluation import EventEvaluationProvider
    EvaluationProviderFactory.register("event", EventEvaluationProvider)
except ImportError:
    logger.info("Event evaluation provider not available (kubernetes package not installed)")

__all__ = [
    "EvaluationProviderFactory",
    "DirectEvaluationProvider",
    "BaselineEvaluationProvider",
    "BatchEvaluationProvider",
]
