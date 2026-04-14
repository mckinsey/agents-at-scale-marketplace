"""Integration test: scheduler + mock K8s API end-to-end A2A round-trip (Task 6.5)."""

import json
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient

from claude_agent_scheduler.config import SchedulerConfig
from claude_agent_scheduler.proxy import create_proxy_app
from claude_agent_scheduler.sandbox_manager import SandboxInfo, SandboxManager


@pytest.fixture
def sandbox_manager() -> SandboxManager:
    config = SchedulerConfig(namespace="test-ns", sandbox_ready_timeout=5)
    with patch("claude_agent_scheduler.sandbox_manager._AsyncK8sHelper"):
        mgr = SandboxManager(config=config)
        mgr._k8s = AsyncMock()
        return mgr


class TestEndToEndA2ARoundTrip:
    def test_new_conversation_creates_sandbox_and_proxies(self, sandbox_manager: SandboxManager) -> None:
        """First message: cache miss → K8s GET 404 → create claim → proxy."""
        # K8s GET returns None (no existing claim)
        sandbox_manager._k8s.get_sandbox_claim = AsyncMock(return_value=None)
        sandbox_manager._k8s.create_sandbox_claim = AsyncMock()
        sandbox_manager._k8s.resolve_sandbox_name = AsyncMock(return_value="sb-e2e-1")
        sandbox_manager._k8s.wait_for_sandbox_ready = AsyncMock()
        sandbox_manager._k8s.patch_claim_annotation = AsyncMock()

        a2a_response = {
            "jsonrpc": "2.0", "id": "1",
            "result": {"artifacts": [{"parts": [{"text": "Hello!"}]}]},
        }

        with patch("claude_agent_scheduler.proxy.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.request = AsyncMock(
                return_value=httpx.Response(200, content=json.dumps(a2a_response).encode(), headers={"content-type": "application/json"})
            )
            mock_client.aclose = AsyncMock()
            mock_client_cls.return_value = mock_client

            app = create_proxy_app(sandbox_manager=sandbox_manager)
            client = TestClient(app, raise_server_exceptions=False)

            response = client.post("/", json={
                "jsonrpc": "2.0", "id": "1", "method": "message/send",
                "params": {"message": {"contextId": "conv-e2e-1", "role": "user", "parts": [{"text": "hi"}]}},
            })

        assert response.status_code == 200
        sandbox_manager._k8s.create_sandbox_claim.assert_called_once()
        sandbox_manager._k8s.resolve_sandbox_name.assert_called_once()

    def test_returning_conversation_uses_cache(self, sandbox_manager: SandboxManager) -> None:
        """Second message: cache hit → no K8s calls for routing."""
        info = SandboxInfo(claim_name="claim-2", sandbox_name="sb-2", service_fqdn="sb-2.test-ns.svc.cluster.local")
        sandbox_manager._cache.put("conv-e2e-2", info)
        sandbox_manager._k8s.patch_claim_annotation = AsyncMock()

        a2a_response = {"jsonrpc": "2.0", "id": "2", "result": {"artifacts": [{"parts": [{"text": "Follow-up"}]}]}}

        with patch("claude_agent_scheduler.proxy.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.request = AsyncMock(
                return_value=httpx.Response(200, content=json.dumps(a2a_response).encode(), headers={"content-type": "application/json"})
            )
            mock_client.aclose = AsyncMock()
            mock_client_cls.return_value = mock_client

            app = create_proxy_app(sandbox_manager=sandbox_manager)
            client = TestClient(app, raise_server_exceptions=False)

            response = client.post("/", json={
                "jsonrpc": "2.0", "id": "2", "method": "message/send",
                "params": {"message": {"contextId": "conv-e2e-2", "role": "user", "parts": [{"text": "follow up"}]}},
            })

        assert response.status_code == 200
        # No sandbox creation calls — routed from cache
        sandbox_manager._k8s.create_sandbox_claim.assert_not_called()

    def test_conflict_handling(self, sandbox_manager: SandboxManager) -> None:
        """Two replicas race: 409 conflict → GET existing claim → proceed."""
        from kubernetes_asyncio.client import ApiException

        sandbox_manager._k8s.get_sandbox_claim = AsyncMock(return_value=None)
        sandbox_manager._k8s.create_sandbox_claim = AsyncMock(side_effect=ApiException(status=409, reason="Conflict"))
        sandbox_manager._k8s.resolve_sandbox_name = AsyncMock(return_value="sb-conflict")
        sandbox_manager._k8s.wait_for_sandbox_ready = AsyncMock()
        sandbox_manager._k8s.patch_claim_annotation = AsyncMock()

        a2a_response = {"jsonrpc": "2.0", "id": "1", "result": {}}

        with patch("claude_agent_scheduler.proxy.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.request = AsyncMock(
                return_value=httpx.Response(200, content=json.dumps(a2a_response).encode(), headers={"content-type": "application/json"})
            )
            mock_client.aclose = AsyncMock()
            mock_client_cls.return_value = mock_client

            app = create_proxy_app(sandbox_manager=sandbox_manager)
            client = TestClient(app, raise_server_exceptions=False)

            response = client.post("/", json={
                "jsonrpc": "2.0", "id": "1", "method": "message/send",
                "params": {"message": {"contextId": "conv-conflict", "role": "user", "parts": [{"text": "hi"}]}},
            })

        assert response.status_code == 200
        # Should still resolve and wait for sandbox despite conflict
        sandbox_manager._k8s.resolve_sandbox_name.assert_called_once()
