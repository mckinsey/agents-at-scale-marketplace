"""Tests for idle reaper logic (Task 8.4)."""

import asyncio
import time
from unittest.mock import AsyncMock, patch

import pytest

from claude_agent_scheduler.config import SchedulerConfig
from claude_agent_scheduler.sandbox_manager import SandboxInfo, SandboxManager


@pytest.fixture
def config() -> SchedulerConfig:
    return SchedulerConfig(session_idle_ttl=60, namespace="test-ns")


@pytest.fixture
def manager(config: SchedulerConfig) -> SandboxManager:
    with patch("claude_agent_scheduler.sandbox_manager._AsyncK8sHelper"):
        mgr = SandboxManager(config=config)
        mgr._k8s = AsyncMock()
        return mgr


class TestIdleReaper:
    @pytest.mark.asyncio
    async def test_expired_sessions_reaped(self, manager: SandboxManager) -> None:
        # Add a session that expired 120 seconds ago
        manager._routing_table["conv-old"] = SandboxInfo(
            claim_name="claim-old",
            sandbox_name="sb-old",
            service_fqdn="sb-old.test-ns.svc.cluster.local",
            last_activity=time.monotonic() - 120,
        )
        # Add a fresh session
        manager._routing_table["conv-new"] = SandboxInfo(
            claim_name="claim-new",
            sandbox_name="sb-new",
            service_fqdn="sb-new.test-ns.svc.cluster.local",
            last_activity=time.monotonic(),
        )

        manager._k8s.delete_sandbox_claim = AsyncMock()

        # Run one reap cycle
        await manager.remove_sandbox("conv-old")

        assert "conv-old" not in manager._routing_table
        assert "conv-new" in manager._routing_table
        manager._k8s.delete_sandbox_claim.assert_called_once_with(name="claim-old", namespace="test-ns")

    @pytest.mark.asyncio
    async def test_activity_reset_prevents_reaping(self, manager: SandboxManager) -> None:
        manager._routing_table["conv-1"] = SandboxInfo(
            claim_name="claim-1",
            sandbox_name="sb-1",
            service_fqdn="sb-1.test-ns.svc.cluster.local",
            last_activity=time.monotonic() - 50,  # 50s ago, TTL is 60s
        )

        # Touch the session (simulates new request)
        manager.touch("conv-1")

        now = time.monotonic()
        info = manager._routing_table["conv-1"]
        assert (now - info.last_activity) < 5  # Should be very recent

    @pytest.mark.asyncio
    async def test_retain_policy_skips_delete(self, manager: SandboxManager) -> None:
        manager._config.shutdown_policy = "Retain"
        manager._routing_table["conv-retain"] = SandboxInfo(
            claim_name="claim-retain",
            sandbox_name="sb-retain",
            service_fqdn="sb-retain.test-ns.svc.cluster.local",
            last_activity=time.monotonic() - 120,
        )

        manager._k8s.delete_sandbox_claim = AsyncMock()
        await manager.remove_sandbox("conv-retain")

        assert "conv-retain" not in manager._routing_table
        manager._k8s.delete_sandbox_claim.assert_not_called()
