import pytest
from evaluator.providers import EvaluationProviderFactory
from evaluator.providers.direct_evaluation import DirectEvaluationProvider
from evaluator.providers.baseline_evaluation import BaselineEvaluationProvider


def test_factory_has_direct_provider():
    registered = EvaluationProviderFactory.get_registered_types()
    assert "direct" in registered


def test_factory_has_baseline_provider():
    registered = EvaluationProviderFactory.get_registered_types()
    assert "baseline" in registered


def test_factory_creates_direct_provider():
    provider = EvaluationProviderFactory.create("direct")
    assert isinstance(provider, DirectEvaluationProvider)
    assert provider.get_evaluation_type() == "direct"


def test_factory_creates_baseline_provider():
    provider = EvaluationProviderFactory.create("baseline")
    assert isinstance(provider, BaselineEvaluationProvider)
    assert provider.get_evaluation_type() == "baseline"


def test_factory_unknown_type_raises():
    with pytest.raises(ValueError, match="No provider registered"):
        EvaluationProviderFactory.create("nonexistent_type")
