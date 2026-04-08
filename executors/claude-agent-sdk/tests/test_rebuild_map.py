"""Tests for startup map rebuild (Task 8.5)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from claude_agent_scheduler.config import SchedulerConfig
from claude_agent_scheduler.sandbox_manager import LABEL_CONVERSATION_ID, LABEL_MANAGED_BY, SandboxManager


def _make_claim(name: str, conversation_id: str, sandbox_name: str = "") -> dict:  # type: ignore[type-arg]
    """Helper: build a SandboxClaim-like dict."""
    claim: dict = {  # type: ignore[type-arg]
        "metadata": {
            "name": name,
            "labels": {
                LABEL_CONVERSATION_ID: conversation_id,
                LABEL_MANAGED_BY: "claude-agent-sdk-scheduler",
            },
        },
        "status": {},
    }
    if sandbox_name:
        claim["status"]["sandbox"] = {"name": sandbox_name}
    return claim


def _make_sandbox(name: str, ready: bool = True) -> dict:  # type: ignore[type-arg]
    """Helper: build a Sandbox-like dict."""
    conditions = []
    if ready:
        conditions.append({"type": "Ready", "status": "True"})
    return {"metadata": {"name": name}, "status": {"conditions": conditions}}


@pytest.fixture
def config() -> SchedulerConfig:
    return SchedulerConfig(namespace="test-ns")


@pytest.fixture
def manager(config: SchedulerConfig) -> SandboxManager:
    with patch("claude_agent_scheduler.sandbox_manager._AsyncK8sHelper"):
        mgr = SandboxManager(config=config)
        mgr._k8s = AsyncMock()
        return mgr


class TestRebuildMap:
    @pytest.mark.asyncio
    async def test_happy_path(self, manager: SandboxManager) -> None:
        claims = [_make_claim("claim-1", "conv-1", "sb-1"), _make_claim("claim-2", "conv-2", "sb-2")]

        with patch("claude_agent_scheduler.sandbox_manager.client") as mock_client:
            mock_api = AsyncMock()
            mock_api.list_namespaced_custom_object = AsyncMock(return_value={"items": claims})
            mock_client.CustomObjectsApi.return_value = mock_api
            with patch("claude_agent_scheduler.sandbox_manager.config"):
                manager._k8s.get_sandbox = AsyncMock(
                    side_effect=lambda name, namespace: _make_sandbox(name, ready=True)
                )

                await manager.rebuild_map()

        assert "conv-1" in manager._routing_table
        assert "conv-2" in manager._routing_table
        assert manager._routing_table["conv-1"].sandbox_name == "sb-1"
        assert manager._routing_table["conv-2"].sandbox_name == "sb-2"

    @pytest.mark.asyncio
    async def test_orphaned_claim_no_sandbox_name(self, manager: SandboxManager) -> None:
        claims = [_make_claim("claim-orphan", "conv-orphan")]  # No sandbox name

        with patch("claude_agent_scheduler.sandbox_manager.client") as mock_client:
            mock_api = AsyncMock()
            mock_api.list_namespaced_custom_object = AsyncMock(return_value={"items": claims})
            mock_client.CustomObjectsApi.return_value = mock_api
            with patch("claude_agent_scheduler.sandbox_manager.config"):
                manager._k8s.delete_sandbox_claim = AsyncMock()

                await manager.rebuild_map()

        assert "conv-orphan" not in manager._routing_table
        manager._k8s.delete_sandbox_claim.assert_called_once_with(name="claim-orphan", namespace="test-ns")

    @pytest.mark.asyncio
    async def test_orphaned_claim_sandbox_not_ready(self, manager: SandboxManager) -> None:
        claims = [_make_claim("claim-stale", "conv-stale", "sb-stale")]

        with patch("claude_agent_scheduler.sandbox_manager.client") as mock_client:
            mock_api = AsyncMock()
            mock_api.list_namespaced_custom_object = AsyncMock(return_value={"items": claims})
            mock_client.CustomObjectsApi.return_value = mock_api
            with patch("claude_agent_scheduler.sandbox_manager.config"):
                manager._k8s.get_sandbox = AsyncMock(return_value=_make_sandbox("sb-stale", ready=False))
                manager._k8s.delete_sandbox_claim = AsyncMock()

                await manager.rebuild_map()

        assert "conv-stale" not in manager._routing_table
        manager._k8s.delete_sandbox_claim.assert_called_once_with(name="claim-stale", namespace="test-ns")
