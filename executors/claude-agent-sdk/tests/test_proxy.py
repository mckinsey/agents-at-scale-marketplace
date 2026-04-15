"""Tests for HTTP proxy logic."""

import json
import uuid
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from fastapi.testclient import TestClient

from claude_agent_scheduler.config import SchedulerConfig
from claude_agent_scheduler.proxy import create_proxy_app
from claude_agent_scheduler.sandbox_manager import SandboxCapacityError, SandboxInfo, SandboxManager


@pytest.fixture
def http_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(timeout=httpx.Timeout(10.0))


@pytest.fixture
def sandbox_manager() -> MagicMock:
    config = SchedulerConfig(namespace="test-ns")
    manager = MagicMock(spec=SandboxManager)
    manager._config = config
    manager.update_last_activity = AsyncMock()
    return manager


class TestProxySandboxError:
    def test_sandbox_creation_failure(self, sandbox_manager: MagicMock, http_client: httpx.AsyncClient) -> None:
        sandbox_manager.create_sandbox = AsyncMock(side_effect=TimeoutError("readiness timeout"))

        fastapi_app = create_proxy_app(sandbox_manager=sandbox_manager, http_client=http_client)
        client = TestClient(fastapi_app, raise_server_exceptions=False)

        # No contextId → is_new=True → create_sandbox
        response = client.post(
            "/",
            json={"jsonrpc": "2.0", "id": "1", "params": {"message": {"role": "user"}}},
        )
        assert response.status_code == 502
        assert "Sandbox creation failed" in response.json()["error"]["message"]

    def test_invalid_context_id_returns_400(self, sandbox_manager: MagicMock, http_client: httpx.AsyncClient) -> None:
        fastapi_app = create_proxy_app(sandbox_manager=sandbox_manager, http_client=http_client)
        client = TestClient(fastapi_app, raise_server_exceptions=False)

        response = client.post(
            "/",
            json={"jsonrpc": "2.0", "id": "1", "params": {"message": {"contextId": "not-a-uuid"}}},
        )
        assert response.status_code == 400
        body = response.json()
        assert body["error"]["code"] == -32602
        assert "Invalid contextId" in body["error"]["message"]

    def test_unknown_session_returns_404(self, sandbox_manager: MagicMock, http_client: httpx.AsyncClient) -> None:
        sandbox_manager.get_sandbox = AsyncMock(return_value=None)

        fastapi_app = create_proxy_app(sandbox_manager=sandbox_manager, http_client=http_client)
        client = TestClient(fastapi_app, raise_server_exceptions=False)

        test_uuid = str(uuid.uuid4())
        response = client.post(
            "/",
            json={"jsonrpc": "2.0", "id": "1", "params": {"message": {"contextId": test_uuid}}},
        )
        assert response.status_code == 404
        body = response.json()
        assert body["error"]["code"] == -32001
        assert "Session not found" in body["error"]["message"]

    def test_capacity_exceeded_returns_503(self, sandbox_manager: MagicMock, http_client: httpx.AsyncClient) -> None:
        sandbox_manager.create_sandbox = AsyncMock(
            side_effect=SandboxCapacityError("Sandbox capacity reached (100/100 active). Retry later.")
        )

        fastapi_app = create_proxy_app(sandbox_manager=sandbox_manager, http_client=http_client)
        client = TestClient(fastapi_app, raise_server_exceptions=False)

        response = client.post(
            "/",
            json={"jsonrpc": "2.0", "id": "1", "params": {"message": {"role": "user"}}},
        )
        assert response.status_code == 503
        assert response.headers.get("retry-after") == "30"
        body = response.json()
        assert body["error"]["code"] == -32000


class TestProxyPassThrough:
    def test_a2a_error_passed_through(self, sandbox_manager: MagicMock) -> None:
        sandbox_info = SandboxInfo(
            claim_name="claim-1",
            sandbox_name="sandbox-1",
            service_fqdn="sandbox-1.test-ns.svc.cluster.local",
        )
        sandbox_manager.create_sandbox = AsyncMock(return_value=sandbox_info)

        error_body = json.dumps({"error": {"code": -32000, "message": "Agent CRD not found"}})
        mock_http_client = AsyncMock(spec=httpx.AsyncClient)
        mock_http_client.request = AsyncMock(
            return_value=httpx.Response(
                400,
                content=error_body.encode(),
                headers={"content-type": "application/json"},
            )
        )

        fastapi_app = create_proxy_app(sandbox_manager=sandbox_manager, http_client=mock_http_client)
        client = TestClient(fastapi_app, raise_server_exceptions=False)

        # No contextId → is_new=True → create_sandbox
        response = client.post(
            "/",
            json={"jsonrpc": "2.0", "id": "1", "params": {"message": {"role": "user", "parts": [{"text": "hi"}]}}},
        )

        assert response.status_code == 400
        assert "Agent CRD not found" in response.text
