"""Integration test: scheduler + mock K8s API end-to-end A2A round-trip."""

import json
import uuid
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
        """First message: no contextId → generate UUID4 → create sandbox → proxy."""
        sandbox_manager._k8s.get_sandbox_claim = AsyncMock(return_value=None)
        sandbox_manager._k8s.create_sandbox_claim = AsyncMock()
        sandbox_manager._k8s.resolve_sandbox_name = AsyncMock(return_value="sb-e2e-1")
        sandbox_manager._k8s.wait_for_sandbox_ready = AsyncMock()
        sandbox_manager._k8s.patch_claim_annotation = AsyncMock()
        sandbox_manager._k8s.list_sandbox_claims = AsyncMock(return_value=[])

        a2a_response = {
            "jsonrpc": "2.0", "id": "1",
            "result": {"artifacts": [{"parts": [{"text": "Hello!"}]}]},
        }

        mock_http_client = AsyncMock(spec=httpx.AsyncClient)
        mock_http_client.request = AsyncMock(
            return_value=httpx.Response(200, content=json.dumps(a2a_response).encode(), headers={"content-type": "application/json"})
        )

        app = create_proxy_app(sandbox_manager=sandbox_manager, http_client=mock_http_client)
        client = TestClient(app, raise_server_exceptions=False)

        # No contextId → is_new=True → create_sandbox
        response = client.post("/", json={
            "jsonrpc": "2.0", "id": "1", "method": "message/send",
            "params": {"message": {"role": "user", "parts": [{"text": "hi"}]}},
        })

        assert response.status_code == 200
        sandbox_manager._k8s.create_sandbox_claim.assert_called_once()
        sandbox_manager._k8s.resolve_sandbox_name.assert_called_once()

    def test_returning_conversation_uses_cache(self, sandbox_manager: SandboxManager) -> None:
        """Second message: valid UUID4 → get_sandbox → cache hit → proxy."""
        test_uuid = str(uuid.uuid4())
        info = SandboxInfo(claim_name="claim-2", sandbox_name="sb-2", service_fqdn="sb-2.test-ns.svc.cluster.local")
        sandbox_manager._cache.put(test_uuid, info)
        sandbox_manager._k8s.patch_claim_annotation = AsyncMock()

        a2a_response = {"jsonrpc": "2.0", "id": "2", "result": {"artifacts": [{"parts": [{"text": "Follow-up"}]}]}}

        mock_http_client = AsyncMock(spec=httpx.AsyncClient)
        mock_http_client.request = AsyncMock(
            return_value=httpx.Response(200, content=json.dumps(a2a_response).encode(), headers={"content-type": "application/json"})
        )

        app = create_proxy_app(sandbox_manager=sandbox_manager, http_client=mock_http_client)
        client = TestClient(app, raise_server_exceptions=False)

        response = client.post("/", json={
            "jsonrpc": "2.0", "id": "2", "method": "message/send",
            "params": {"message": {"contextId": test_uuid, "role": "user", "parts": [{"text": "follow up"}]}},
        })

        assert response.status_code == 200
        # No sandbox creation calls — routed from cache
        sandbox_manager._k8s.create_sandbox_claim.assert_not_called()

    def test_conflict_handling(self, sandbox_manager: SandboxManager) -> None:
        """Two replicas race: 409 conflict → proceed with existing claim."""
        from kubernetes_asyncio.client import ApiException

        sandbox_manager._k8s.get_sandbox_claim = AsyncMock(return_value=None)
        sandbox_manager._k8s.create_sandbox_claim = AsyncMock(side_effect=ApiException(status=409, reason="Conflict"))
        sandbox_manager._k8s.resolve_sandbox_name = AsyncMock(return_value="sb-conflict")
        sandbox_manager._k8s.wait_for_sandbox_ready = AsyncMock()
        sandbox_manager._k8s.patch_claim_annotation = AsyncMock()
        sandbox_manager._k8s.list_sandbox_claims = AsyncMock(return_value=[])

        a2a_response = {"jsonrpc": "2.0", "id": "1", "result": {}}

        mock_http_client = AsyncMock(spec=httpx.AsyncClient)
        mock_http_client.request = AsyncMock(
            return_value=httpx.Response(200, content=json.dumps(a2a_response).encode(), headers={"content-type": "application/json"})
        )

        app = create_proxy_app(sandbox_manager=sandbox_manager, http_client=mock_http_client)
        client = TestClient(app, raise_server_exceptions=False)

        # No contextId → is_new=True → create_sandbox (which gets 409)
        response = client.post("/", json={
            "jsonrpc": "2.0", "id": "1", "method": "message/send",
            "params": {"message": {"role": "user", "parts": [{"text": "hi"}]}},
        })

        assert response.status_code == 200
        sandbox_manager._k8s.resolve_sandbox_name.assert_called_once()

    def test_admission_control_returns_503(self, sandbox_manager: SandboxManager) -> None:
        """Capacity limit reached → 503 with Retry-After."""
        sandbox_manager._config.max_active_sandboxes = 2
        sandbox_manager._k8s.list_sandbox_claims = AsyncMock(return_value=[{}, {}])  # 2 claims = at capacity

        mock_http_client = AsyncMock(spec=httpx.AsyncClient)

        app = create_proxy_app(sandbox_manager=sandbox_manager, http_client=mock_http_client)
        client = TestClient(app, raise_server_exceptions=False)

        response = client.post("/", json={
            "jsonrpc": "2.0", "id": "1", "method": "message/send",
            "params": {"message": {"role": "user", "parts": [{"text": "hi"}]}},
        })

        assert response.status_code == 503
        assert response.headers.get("retry-after") == "30"
