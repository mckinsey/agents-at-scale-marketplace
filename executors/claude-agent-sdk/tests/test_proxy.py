"""Tests for HTTP proxy logic (Task 6.1 - ensure_sandbox via proxy)."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient

from claude_agent_scheduler.config import SchedulerConfig
from claude_agent_scheduler.proxy import create_proxy_app
from claude_agent_scheduler.sandbox_manager import SandboxInfo, SandboxManager


@pytest.fixture
def sandbox_manager() -> MagicMock:
    config = SchedulerConfig(namespace="test-ns")
    manager = MagicMock(spec=SandboxManager)
    manager._config = config
    manager.update_last_activity = AsyncMock()
    return manager


class TestProxySandboxError:
    def test_sandbox_creation_failure(self, sandbox_manager: MagicMock) -> None:
        sandbox_manager.ensure_sandbox = AsyncMock(side_effect=TimeoutError("readiness timeout"))

        fastapi_app = create_proxy_app(sandbox_manager=sandbox_manager)
        client = TestClient(fastapi_app, raise_server_exceptions=False)

        response = client.post(
            "/",
            json={"jsonrpc": "2.0", "id": "1", "params": {"message": {"contextId": "conv-fail"}}},
        )
        assert response.status_code == 502
        assert "Sandbox creation failed" in response.json()["error"]


class TestProxyPassThrough:
    def test_a2a_error_passed_through(self, sandbox_manager: MagicMock) -> None:
        sandbox_info = SandboxInfo(
            claim_name="claim-1",
            sandbox_name="sandbox-1",
            service_fqdn="sandbox-1.test-ns.svc.cluster.local",
        )
        sandbox_manager.ensure_sandbox = AsyncMock(return_value=(sandbox_info, True))

        error_body = json.dumps({"error": {"code": -32000, "message": "Agent CRD not found"}})
        mock_response = httpx.Response(
            400,
            content=error_body.encode(),
            headers={"content-type": "application/json"},
        )

        with patch("claude_agent_scheduler.proxy.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.request = AsyncMock(return_value=mock_response)
            mock_client.aclose = AsyncMock()
            mock_client_cls.return_value = mock_client

            fastapi_app = create_proxy_app(sandbox_manager=sandbox_manager)
            client = TestClient(fastapi_app, raise_server_exceptions=False)

            response = client.post(
                "/",
                json={"jsonrpc": "2.0", "id": "1", "params": {"message": {"contextId": "conv-err"}}},
            )

        assert response.status_code == 400
        assert "Agent CRD not found" in response.text
