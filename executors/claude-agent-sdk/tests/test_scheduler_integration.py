"""Integration test: scheduler + mock sandbox end-to-end A2A round-trip (Task 8.6)."""

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
        """Simulate: first message -> sandbox creation -> proxy -> response."""
        # Mock K8s operations for sandbox creation
        sandbox_manager._k8s.create_sandbox_claim = AsyncMock()
        sandbox_manager._k8s.resolve_sandbox_name = AsyncMock(return_value="sb-e2e-1")
        sandbox_manager._k8s.wait_for_sandbox_ready = AsyncMock()

        # Mock the upstream executor response
        a2a_response = {
            "jsonrpc": "2.0",
            "id": "1",
            "result": {
                "artifacts": [{"parts": [{"text": "Hello from the sandbox!"}]}],
            },
        }

        with patch("claude_agent_scheduler.proxy.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.request = AsyncMock(
                return_value=httpx.Response(
                    200,
                    content=json.dumps(a2a_response).encode(),
                    headers={"content-type": "application/json"},
                )
            )
            mock_client.aclose = AsyncMock()
            mock_client_cls.return_value = mock_client

            app = create_proxy_app(sandbox_manager=sandbox_manager)
            client = TestClient(app, raise_server_exceptions=False)

            a2a_request = {
                "jsonrpc": "2.0",
                "id": "1",
                "method": "message/send",
                "params": {
                    "message": {"role": "user", "parts": [{"text": "What is Ark?"}]},
                },
                "context_id": "conv-e2e-1",
            }

            response = client.post("/", json=a2a_request)

        assert response.status_code == 200
        body = response.json()
        assert body["result"]["artifacts"][0]["parts"][0]["text"] == "Hello from the sandbox!"

        # Verify sandbox was created
        sandbox_manager._k8s.create_sandbox_claim.assert_called_once()
        sandbox_manager._k8s.resolve_sandbox_name.assert_called_once()
        sandbox_manager._k8s.wait_for_sandbox_ready.assert_called_once()

        # Verify routing table was populated
        assert "conv-e2e-1" in sandbox_manager._routing_table
        info = sandbox_manager._routing_table["conv-e2e-1"]
        assert info.sandbox_name == "sb-e2e-1"

    def test_returning_conversation_reuses_sandbox(self, sandbox_manager: SandboxManager) -> None:
        """Simulate: second message -> existing sandbox -> proxy -> response."""
        # Pre-populate the routing table
        sandbox_manager._routing_table["conv-e2e-2"] = SandboxInfo(
            claim_name="claim-e2e-2",
            sandbox_name="sb-e2e-2",
            service_fqdn="sb-e2e-2.test-ns.svc.cluster.local",
        )

        a2a_response = {
            "jsonrpc": "2.0",
            "id": "2",
            "result": {"artifacts": [{"parts": [{"text": "Follow-up response"}]}]},
        }

        with patch("claude_agent_scheduler.proxy.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.request = AsyncMock(
                return_value=httpx.Response(
                    200,
                    content=json.dumps(a2a_response).encode(),
                    headers={"content-type": "application/json"},
                )
            )
            mock_client.aclose = AsyncMock()
            mock_client_cls.return_value = mock_client

            app = create_proxy_app(sandbox_manager=sandbox_manager)
            client = TestClient(app, raise_server_exceptions=False)

            response = client.post(
                "/",
                json={"context_id": "conv-e2e-2", "message": {"role": "user", "parts": [{"text": "follow up"}]}},
            )

        assert response.status_code == 200
        # No new sandbox creation should have happened
        sandbox_manager._k8s.create_sandbox_claim.assert_not_called()
