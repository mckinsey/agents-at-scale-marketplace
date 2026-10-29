"""Tests for resolving OpenAI credentials from an Ark Agent's referenced Model."""

import base64
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from kubernetes.client.exceptions import ApiException

from openai_responses_executor import agent_credentials
from openai_responses_executor.agent_credentials import (
    AgentContext,
    _k8s_error,
    _resolve_secret,
    _resolve_value_source,
    parse_agent_ref,
    resolve_agent_context,
    resolve_agent_openai_credentials,
)


class _AsyncCM:
    def __init__(self, value):
        self._value = value

    async def __aenter__(self):
        return self._value

    async def __aexit__(self, *exc):
        return False


@pytest.fixture(autouse=True)
def _clear_context_cache():
    agent_credentials._context_cache.clear()
    yield
    agent_credentials._context_cache.clear()


class TestParseAgentRef:
    def test_splits_namespace_and_name(self):
        assert parse_agent_ref("team-a/my-agent") == ("team-a", "my-agent")

    def test_bare_name_uses_default_namespace(self):
        with patch.dict("os.environ", {"POD_NAMESPACE": "prod"}, clear=True):
            assert parse_agent_ref("my-agent") == ("prod", "my-agent")


class TestKError:
    def test_404_maps_to_not_found(self):
        err = _k8s_error("Agent", "ns/name", ApiException(status=404, reason="Not Found"))
        assert "not found" in str(err)

    def test_403_maps_to_forbidden_with_rbac_hint(self):
        err = _k8s_error("Model", "ns/name", ApiException(status=403, reason="Forbidden"))
        assert "forbidden" in str(err)
        assert "RBAC" in str(err)


class TestResolveSecret:
    @pytest.mark.asyncio
    async def test_decodes_base64_secret_value(self):
        encoded = base64.b64encode(b"sk-secret").decode()
        mock_secret_client = MagicMock()
        mock_secret_client.get_secret_value = AsyncMock(return_value={"value": encoded})

        with patch.object(agent_credentials, "_ensure_k8s_config"), \
             patch.object(agent_credentials, "SecretClient", return_value=mock_secret_client) as mock_cls:
            value = await _resolve_secret({"name": "openai-secret", "key": "apiKey"}, "team-a")

        mock_cls.assert_called_once_with(namespace="team-a")
        mock_secret_client.get_secret_value.assert_awaited_once_with("openai-secret", "apiKey")
        assert value == "sk-secret"

    @pytest.mark.asyncio
    async def test_k8s_failure_raises_value_error_naming_the_secret(self):
        # Swallowing this would surface as a baffling "apiKey resolved empty";
        # the error must name the failing Secret.
        mock_secret_client = MagicMock()
        mock_secret_client.get_secret_value = AsyncMock(side_effect=RuntimeError("rbac denied"))

        with patch.object(agent_credentials, "_ensure_k8s_config"), \
             patch.object(agent_credentials, "SecretClient", return_value=mock_secret_client):
            with pytest.raises(ValueError, match="team-a/openai-secret"):
                await _resolve_secret({"name": "openai-secret", "key": "apiKey"}, "team-a")


class TestResolveValueSource:
    """The direct-value / secret / configmap cascade, the core of credential resolution."""

    @pytest.mark.asyncio
    async def test_direct_value_wins_over_value_from(self):
        vs = {"value": "sk-direct", "valueFrom": {"secretKeyRef": {"name": "s", "key": "k"}}}
        assert await _resolve_value_source(vs, "team-a") == "sk-direct"

    @pytest.mark.asyncio
    async def test_secret_key_ref_delegates_to_resolve_secret(self):
        vs = {"valueFrom": {"secretKeyRef": {"name": "s", "key": "k"}}}
        with patch.object(agent_credentials, "_resolve_secret", AsyncMock(return_value="sk-from-secret")) as mock_resolve:
            value = await _resolve_value_source(vs, "team-a")

        mock_resolve.assert_awaited_once_with({"name": "s", "key": "k"}, "team-a")
        assert value == "sk-from-secret"

    @pytest.mark.asyncio
    async def test_falls_back_to_configmap_when_secret_resolves_empty(self):
        vs = {"valueFrom": {"secretKeyRef": {"name": "s", "key": "k"}, "configMapKeyRef": {"name": "c", "key": "k"}}}
        with patch.object(agent_credentials, "_resolve_secret", AsyncMock(return_value="")), \
             patch.object(agent_credentials, "_resolve_configmap", AsyncMock(return_value="from-cm")) as mock_cm:
            value = await _resolve_value_source(vs, "team-a")

        mock_cm.assert_awaited_once_with({"name": "c", "key": "k"}, "team-a")
        assert value == "from-cm"


class TestResolveAgentOpenaiCredentials:
    @pytest.mark.asyncio
    async def test_returns_none_when_context_is_none(self):
        with patch.object(agent_credentials, "resolve_agent_context", AsyncMock(return_value=None)):
            assert await resolve_agent_openai_credentials("agent-a", "team-a") is None


class TestResolveAgentContext:
    def _agent(self, model_ref=None, prompt="be helpful"):
        return SimpleNamespace(spec=SimpleNamespace(model_ref=model_ref, prompt=prompt))

    def _model(self, config=None, model_vs=None):
        return SimpleNamespace(spec=SimpleNamespace(config=config, model=model_vs))

    def _ark_client(self, agent=None, agent_error=None, model=None, model_error=None):
        ark = MagicMock()
        if agent_error is not None:
            ark.agents.a_get = AsyncMock(side_effect=agent_error)
        else:
            ark.agents.a_get = AsyncMock(return_value=agent)
        if model_error is not None:
            ark.models.a_get = AsyncMock(side_effect=model_error)
        else:
            ark.models.a_get = AsyncMock(return_value=model)
        return ark

    @pytest.mark.asyncio
    async def test_no_model_ref_returns_none_without_fetching_model(self):
        ark = self._ark_client(agent=self._agent(model_ref=None))
        with patch.object(agent_credentials, "with_ark_client", return_value=_AsyncCM(ark)):
            result = await resolve_agent_context("agent-a", "team-a")

        assert result is None
        ark.models.a_get.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_model_without_openai_config_returns_none(self):
        model_ref = {"name": "model-a"}
        model = self._model(config={"anthropic": {}})
        ark = self._ark_client(agent=self._agent(model_ref=model_ref), model=model)
        with patch.object(agent_credentials, "with_ark_client", return_value=_AsyncCM(ark)):
            result = await resolve_agent_context("agent-a", "team-a")

        assert result is None

    @pytest.mark.asyncio
    async def test_resolves_full_context_via_secret(self):
        model_ref = {"name": "model-a"}
        model = self._model(config={"openai": {"apiKey": {"value": "sk-abc"}, "baseUrl": {"value": "https://x"}}})
        agent = self._agent(model_ref=model_ref, prompt="be helpful")
        ark = self._ark_client(agent=agent, model=model)

        with patch.object(agent_credentials, "with_ark_client", return_value=_AsyncCM(ark)):
            ctx = await resolve_agent_context("agent-a", "team-a")

        ark.agents.a_get.assert_awaited_once_with("agent-a", "team-a")
        ark.models.a_get.assert_awaited_once_with("model-a", "team-a")
        assert ctx == AgentContext(api_key="sk-abc", base_url="https://x", model_name="model-a", instructions="be helpful")

    @pytest.mark.asyncio
    async def test_empty_resolved_api_key_raises(self):
        model_ref = {"name": "model-a"}
        model = self._model(config={"openai": {"apiKey": {"value": ""}}})
        ark = self._ark_client(agent=self._agent(model_ref=model_ref), model=model)

        with patch.object(agent_credentials, "with_ark_client", return_value=_AsyncCM(ark)):
            with pytest.raises(ValueError, match="apiKey resolved"):
                await resolve_agent_context("agent-a", "team-a")

    @pytest.mark.asyncio
    async def test_agent_not_found_raises_mapped_value_error(self):
        ark = self._ark_client(agent_error=ApiException(status=404, reason="Not Found"))
        with patch.object(agent_credentials, "with_ark_client", return_value=_AsyncCM(ark)):
            with pytest.raises(ValueError, match="Agent team-a/agent-a not found"):
                await resolve_agent_context("agent-a", "team-a")

    @pytest.mark.asyncio
    async def test_unexpected_exception_propagates(self):
        # Only ValueError (real misconfiguration) is meant to be caught and
        # remapped; anything else must not be flattened into "no model".
        ark = self._ark_client(agent_error=RuntimeError("network blip"))
        with patch.object(agent_credentials, "with_ark_client", return_value=_AsyncCM(ark)):
            with pytest.raises(RuntimeError, match="network blip"):
                await resolve_agent_context("agent-a", "team-a")

    @pytest.mark.asyncio
    async def test_result_is_cached_within_ttl(self):
        model_ref = {"name": "model-a"}
        model = self._model(config={"openai": {"apiKey": {"value": "sk-abc"}}})
        ark = self._ark_client(agent=self._agent(model_ref=model_ref), model=model)

        with patch.object(agent_credentials, "with_ark_client", return_value=_AsyncCM(ark)):
            await resolve_agent_context("agent-a", "team-a")
            await resolve_agent_context("agent-a", "team-a")

        ark.agents.a_get.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_failures_are_never_cached(self):
        model_ref = {"name": "model-a"}
        model = self._model(config={"openai": {"apiKey": {"value": ""}}})
        ark = self._ark_client(agent=self._agent(model_ref=model_ref), model=model)

        with patch.object(agent_credentials, "with_ark_client", return_value=_AsyncCM(ark)):
            with pytest.raises(ValueError):
                await resolve_agent_context("agent-a", "team-a")

        assert ("team-a", "agent-a") not in agent_credentials._context_cache
