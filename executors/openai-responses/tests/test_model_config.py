"""Tests for ModelConfig Pydantic validation."""

import pytest
from pydantic import ValidationError
from unittest.mock import MagicMock

from openai_responses_executor.models import AzureModelConfig, OpenAIModelConfig, ModelConfig


def _model(name="gpt-5", provider="openai", config=None):
    m = MagicMock()
    m.name = name
    m.type = provider
    m.config = config or {}
    return m


def _request(model):
    req = MagicMock()
    req.agent.model = model
    return req


class TestAzureModelConfig:
    def test_valid(self):
        cfg = AzureModelConfig(apiKey="key", baseUrl="https://example.com", apiVersion="2024-04-01-preview")
        assert cfg.apiKey == "key"
        assert cfg.baseUrl == "https://example.com"
        assert cfg.apiVersion == "2024-04-01-preview"

    def test_missing_api_key(self):
        with pytest.raises(ValidationError, match="apiKey"):
            AzureModelConfig(baseUrl="https://example.com", apiVersion="2024-04-01-preview")

    def test_missing_base_url(self):
        with pytest.raises(ValidationError, match="baseUrl"):
            AzureModelConfig(apiKey="key", apiVersion="2024-04-01-preview")

    def test_missing_api_version(self):
        with pytest.raises(ValidationError, match="apiVersion"):
            AzureModelConfig(apiKey="key", baseUrl="https://example.com")


class TestOpenAIModelConfig:
    def test_valid_with_base_url(self):
        cfg = OpenAIModelConfig(apiKey="sk-test", baseUrl="https://proxy.example.com")
        assert cfg.baseUrl == "https://proxy.example.com"

    def test_valid_without_base_url(self):
        cfg = OpenAIModelConfig(apiKey="sk-test")
        assert cfg.baseUrl is None

    def test_missing_api_key(self):
        with pytest.raises(ValidationError, match="apiKey"):
            OpenAIModelConfig(baseUrl="https://proxy.example.com")


class TestModelConfigFromRequest:
    def test_azure_provider(self):
        model = _model("gpt-5", "azure", {
            "azure": {"apiKey": "key", "baseUrl": "https://azure.example.com", "apiVersion": "2024-04-01-preview"}
        })
        mc = ModelConfig.from_request(_request(model))
        assert mc.provider == "azure"
        assert mc.api_key == "key"
        assert mc.base_url == "https://azure.example.com"
        assert mc.api_version == "2024-04-01-preview"

    def test_openai_provider(self):
        model = _model("gpt-5", "openai", {"openai": {"apiKey": "sk-test"}})
        mc = ModelConfig.from_request(_request(model))
        assert mc.provider == "openai"
        assert mc.api_key == "sk-test"
        assert mc.base_url is None

    def test_openai_with_base_url(self):
        model = _model("gpt-5", "openai", {"openai": {"apiKey": "sk-test", "baseUrl": "https://proxy.example.com"}})
        mc = ModelConfig.from_request(_request(model))
        assert mc.base_url == "https://proxy.example.com"

    def test_azure_missing_base_url_raises(self):
        model = _model("gpt-5", "azure", {
            "azure": {"apiKey": "key", "apiVersion": "2024-04-01-preview"}
        })
        with pytest.raises(ValidationError, match="baseUrl"):
            ModelConfig.from_request(_request(model))

    def test_azure_missing_api_version_raises(self):
        model = _model("gpt-5", "azure", {
            "azure": {"apiKey": "key", "baseUrl": "https://azure.example.com"}
        })
        with pytest.raises(ValidationError, match="apiVersion"):
            ModelConfig.from_request(_request(model))

    def test_azure_missing_api_key_raises(self):
        model = _model("gpt-5", "azure", {
            "azure": {"baseUrl": "https://azure.example.com", "apiVersion": "2024-04-01-preview"}
        })
        with pytest.raises(ValidationError, match="apiKey"):
            ModelConfig.from_request(_request(model))

    def test_openai_missing_api_key_raises(self):
        model = _model("gpt-5", "openai", {"openai": {"baseUrl": "https://proxy.example.com"}})
        with pytest.raises(ValidationError, match="apiKey"):
            ModelConfig.from_request(_request(model))

    def test_no_model_raises(self):
        req = MagicMock()
        req.agent.model = None
        with pytest.raises(ValueError, match="model"):
            ModelConfig.from_request(req)

    def test_unknown_provider_falls_back_to_openai_path(self):
        model = _model("gpt-5", "unknown", {})
        with pytest.raises(ValidationError):
            ModelConfig.from_request(_request(model))
