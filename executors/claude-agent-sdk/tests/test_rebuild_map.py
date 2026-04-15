"""Tests for startup cache warming (Tasks 6.4)."""

from unittest.mock import AsyncMock, patch

import pytest

from claude_agent_scheduler.config import SchedulerConfig
from claude_agent_scheduler.sandbox_manager import (
    LABEL_CONVERSATION_ID,
    LABEL_MANAGED_BY,
    SandboxManager,
)


def _make_claim(name: str, conversation_id: str, sandbox_name: str = "") -> dict:  # type: ignore[type-arg]
    claim: dict = {  # type: ignore[type-arg]
        "metadata": {
            "name": name,
            "labels": {
                LABEL_CONVERSATION_ID: conversation_id,
                LABEL_MANAGED_BY: "claude-agent-sdk-scheduler",
            },
            "annotations": {},
        },
        "status": {},
    }
    if sandbox_name:
        claim["status"]["sandbox"] = {"name": sandbox_name}
    return claim


def _make_sandbox(name: str, ready: bool = True) -> dict:  # type: ignore[type-arg]
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


class TestWarmCache:
    @pytest.mark.asyncio
    async def test_happy_path(self, manager: SandboxManager) -> None:
        claims = [_make_claim("claim-1", "conv-1", "sb-1"), _make_claim("claim-2", "conv-2", "sb-2")]
        manager._k8s.list_sandbox_claims = AsyncMock(return_value=claims)
        manager._k8s.get_sandbox = AsyncMock(side_effect=lambda name, namespace: _make_sandbox(name, ready=True))

        await manager.warm_cache()

        assert manager._cache.get("conv-1") is not None
        assert manager._cache.get("conv-2") is not None
        assert manager._cache.get("conv-1").sandbox_name == "sb-1"

    @pytest.mark.asyncio
    async def test_orphaned_claim_no_sandbox_name(self, manager: SandboxManager) -> None:
        claims = [_make_claim("claim-orphan", "conv-orphan")]
        manager._k8s.list_sandbox_claims = AsyncMock(return_value=claims)
        manager._k8s.delete_sandbox_claim = AsyncMock()

        await manager.warm_cache()

        assert manager._cache.get("conv-orphan") is None
        manager._k8s.delete_sandbox_claim.assert_called_once_with("claim-orphan", "test-ns")

    @pytest.mark.asyncio
    async def test_orphaned_claim_sandbox_not_ready(self, manager: SandboxManager) -> None:
        claims = [_make_claim("claim-stale", "conv-stale", "sb-stale")]
        manager._k8s.list_sandbox_claims = AsyncMock(return_value=claims)
        manager._k8s.get_sandbox = AsyncMock(return_value=_make_sandbox("sb-stale", ready=False))
        manager._k8s.delete_sandbox_claim = AsyncMock()

        await manager.warm_cache()

        assert manager._cache.get("conv-stale") is None
        manager._k8s.delete_sandbox_claim.assert_called_once_with("claim-stale", "test-ns")
