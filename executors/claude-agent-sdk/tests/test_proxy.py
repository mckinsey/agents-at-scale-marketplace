"""Tests for HTTP proxy logic."""

import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from ark_sdk.extensions.query import QUERY_EXTENSION_METADATA_KEY
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


def _a2a_body_with_query_ref(
    query_name: str = "q-1",
    query_namespace: str = "test-ns",
    context_id: str | None = None,
) -> dict:
    """Build an A2A JSON-RPC body that includes query extension metadata."""
    message: dict = {
        "role": "user",
        "metadata": {
            QUERY_EXTENSION_METADATA_KEY: {
                "name": query_name,
                "namespace": query_namespace,
            },
        },
    }
    if context_id is not None:
        message["contextId"] = context_id
    return {"jsonrpc": "2.0", "id": "1", "params": {"message": message}}


class TestProxyQueryStatus:
    """Tests for Query provisioning status updates during sandbox lifecycle."""

    def test_new_conversation_triggers_provisioning_and_running(
        self, sandbox_manager: MagicMock, http_client: httpx.AsyncClient,
    ) -> None:
        """3.1: new conversation triggers provisioning and running status updates around create_sandbox."""
        sandbox_info = SandboxInfo(
            claim_name="claim-1",
            sandbox_name="sandbox-1",
            service_fqdn="sandbox-1.test-ns.svc.cluster.local",
        )
        sandbox_manager.create_sandbox = AsyncMock(return_value=sandbox_info)

        mock_http = AsyncMock(spec=httpx.AsyncClient)
        mock_http.request = AsyncMock(
            return_value=httpx.Response(200, content=b'{"ok":true}', headers={"content-type": "application/json"}),
        )

        mock_updater = AsyncMock()

        with patch("claude_agent_scheduler.proxy.QueryStatusUpdater", return_value=mock_updater):
            fastapi_app = create_proxy_app(sandbox_manager=sandbox_manager, http_client=mock_http)
            client = TestClient(fastapi_app, raise_server_exceptions=False)

            response = client.post("/", json=_a2a_body_with_query_ref())

        assert response.status_code == 200
        assert mock_updater.update_query_phase.await_count == 2
        calls = mock_updater.update_query_phase.await_args_list
        assert calls[0].args == ("provisioning", "ExecutorProvisioning", "Provisioning sandbox")
        assert calls[1].args == ("running", "QueryRunning", "Query is running")

    def test_existing_conversation_skips_status_updates(
        self, sandbox_manager: MagicMock,
    ) -> None:
        """3.2: existing conversation (cache hit) skips status updates."""
        sandbox_info = SandboxInfo(
            claim_name="claim-1",
            sandbox_name="sandbox-1",
            service_fqdn="sandbox-1.test-ns.svc.cluster.local",
        )
        sandbox_manager.get_sandbox = AsyncMock(return_value=sandbox_info)

        mock_http = AsyncMock(spec=httpx.AsyncClient)
        mock_http.request = AsyncMock(
            return_value=httpx.Response(200, content=b'{"ok":true}', headers={"content-type": "application/json"}),
        )

        mock_updater = AsyncMock()

        with patch("claude_agent_scheduler.proxy.QueryStatusUpdater", return_value=mock_updater):
            fastapi_app = create_proxy_app(sandbox_manager=sandbox_manager, http_client=mock_http)
            client = TestClient(fastapi_app, raise_server_exceptions=False)

            # Provide a valid contextId so is_new=False
            test_uuid = str(uuid.uuid4())
            response = client.post("/", json=_a2a_body_with_query_ref(context_id=test_uuid))

        assert response.status_code == 200
        mock_updater.update_query_phase.assert_not_awaited()

    def test_status_update_failure_does_not_block(
        self, sandbox_manager: MagicMock, http_client: httpx.AsyncClient,
    ) -> None:
        """3.3: status update failure does not block sandbox creation or proxying."""
        sandbox_info = SandboxInfo(
            claim_name="claim-1",
            sandbox_name="sandbox-1",
            service_fqdn="sandbox-1.test-ns.svc.cluster.local",
        )
        sandbox_manager.create_sandbox = AsyncMock(return_value=sandbox_info)

        mock_http = AsyncMock(spec=httpx.AsyncClient)
        mock_http.request = AsyncMock(
            return_value=httpx.Response(200, content=b'{"ok":true}', headers={"content-type": "application/json"}),
        )

        mock_updater = AsyncMock()
        mock_updater.update_query_phase = AsyncMock(side_effect=Exception("K8s API unreachable"))

        with patch("claude_agent_scheduler.proxy.QueryStatusUpdater", return_value=mock_updater):
            fastapi_app = create_proxy_app(sandbox_manager=sandbox_manager, http_client=mock_http)
            client = TestClient(fastapi_app, raise_server_exceptions=False)

            response = client.post("/", json=_a2a_body_with_query_ref())

        # Request should succeed despite status update failures
        assert response.status_code == 200
        sandbox_manager.create_sandbox.assert_awaited_once()

    def test_sandbox_creation_failure_after_provisioning_signal(
        self, sandbox_manager: MagicMock, http_client: httpx.AsyncClient,
    ) -> None:
        """3.4: sandbox creation failure after provisioning signal returns correct error response."""
        sandbox_manager.create_sandbox = AsyncMock(side_effect=TimeoutError("readiness timeout"))

        mock_updater = AsyncMock()

        with patch("claude_agent_scheduler.proxy.QueryStatusUpdater", return_value=mock_updater):
            fastapi_app = create_proxy_app(sandbox_manager=sandbox_manager, http_client=http_client)
            client = TestClient(fastapi_app, raise_server_exceptions=False)

            response = client.post("/", json=_a2a_body_with_query_ref())

        assert response.status_code == 502
        assert "Sandbox creation failed" in response.json()["error"]["message"]
        # Provisioning was signaled before failure
        assert mock_updater.update_query_phase.await_count == 1
        assert mock_updater.update_query_phase.await_args_list[0].args[0] == "provisioning"


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
