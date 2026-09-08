"""Tests for sandbox admission control under concurrency."""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from claude_agent_scheduler.config import SchedulerConfig
from claude_agent_scheduler.sandbox_manager import (
    LABEL_CONVERSATION_ID,
    LABEL_MANAGED_BY,
    MANAGED_BY_VALUE,
    SandboxCapacityError,
    SandboxManager,
)

API_LATENCY = 0.002


def _make_claim(name: str, conversation_id: str, sandbox_name: str = "") -> dict:  # type: ignore[type-arg]
    claim: dict = {  # type: ignore[type-arg]
        "metadata": {
            "name": name,
            "labels": {LABEL_CONVERSATION_ID: conversation_id, LABEL_MANAGED_BY: MANAGED_BY_VALUE},
            "annotations": {},
        },
        "status": {},
    }
    if sandbox_name:
        claim["status"]["sandbox"] = {"name": sandbox_name}
    return claim


@pytest.fixture
def manager() -> SandboxManager:
    config = SchedulerConfig(namespace="test-ns", sandbox_ready_timeout=5)
    with patch("claude_agent_scheduler.sandbox_manager._AsyncK8sHelper"):
        mgr = SandboxManager(config=config)
        mgr._k8s = AsyncMock()
        return mgr


def _wire_creation(manager: SandboxManager) -> list[str]:
    """Mock the creation path with awaits, so concurrent callers interleave.

    A CREATE that returns without yielding to the event loop hides races that a
    real API round-trip exposes.
    """
    created: list[str] = []

    async def fake_create(  # type: ignore[type-arg]
        name: str, template: str, namespace: str, labels: dict | None = None
    ) -> dict:
        await asyncio.sleep(API_LATENCY)
        created.append(name)
        await asyncio.sleep(API_LATENCY)
        return {"metadata": {"name": name}}

    async def fake_list(namespace: str, label_selector: str) -> list:  # type: ignore[type-arg]
        await asyncio.sleep(API_LATENCY)
        return [_make_claim(n, n, f"sb-{n}") for n in created]

    manager._k8s.create_sandbox_claim = fake_create
    manager._k8s.list_sandbox_claims = fake_list
    manager._k8s.resolve_sandbox_name = AsyncMock(
        side_effect=lambda claim_name, namespace, timeout: f"sb-{claim_name}"
    )
    manager._k8s.wait_for_sandbox_ready = AsyncMock()
    manager._k8s.delete_sandbox_claim = AsyncMock()
    manager._k8s.get_sandbox_claim = AsyncMock(return_value=None)
    return created


class TestAdmissionControlConcurrency:
    @pytest.mark.asyncio
    async def test_cap_holds_under_simultaneous_creates(self, manager: SandboxManager) -> None:
        """A burst of new conversations must not exceed the cap.

        Regression test: the count check used to LIST before creating, so every
        request in a burst read the same stale count and all were admitted.
        """
        manager._config.max_active_sandboxes = 5
        created = _wire_creation(manager)

        results = await asyncio.gather(
            *[manager.create_sandbox(f"conv-{i}") for i in range(50)], return_exceptions=True
        )

        rejected = [r for r in results if isinstance(r, SandboxCapacityError)]
        unexpected = [
            r for r in results if isinstance(r, Exception) and not isinstance(r, SandboxCapacityError)
        ]
        assert unexpected == []
        assert len(created) == 5
        assert len(rejected) == 45

    @pytest.mark.asyncio
    async def test_zero_means_unlimited(self, manager: SandboxManager) -> None:
        manager._config.max_active_sandboxes = 0
        created = _wire_creation(manager)

        results = await asyncio.gather(
            *[manager.create_sandbox(f"conv-{i}") for i in range(20)], return_exceptions=True
        )

        assert [r for r in results if isinstance(r, Exception)] == []
        assert len(created) == 20

    @pytest.mark.asyncio
    async def test_capacity_is_reusable_after_reap(self, manager: SandboxManager) -> None:
        """Freeing claims outside the scheduler must free capacity within a reap cycle."""
        manager._config.max_active_sandboxes = 2
        _wire_creation(manager)

        await manager.create_sandbox("conv-1")
        await manager.create_sandbox("conv-2")
        with pytest.raises(SandboxCapacityError):
            await manager.create_sandbox("conv-3")

        manager._k8s.list_sandbox_claims = AsyncMock(return_value=[])
        await manager._reap_once()

        assert manager._active_count == 0
        await manager.create_sandbox("conv-4")


class TestAdmissionControlAccounting:
    @pytest.mark.asyncio
    async def test_failed_provision_releases_capacity(self, manager: SandboxManager) -> None:
        manager._config.max_active_sandboxes = 1
        _wire_creation(manager)
        manager._k8s.resolve_sandbox_name = AsyncMock(side_effect=TimeoutError("readiness timeout"))

        with pytest.raises(TimeoutError):
            await manager.create_sandbox("conv-doomed")

        assert manager._in_flight == 0
        assert manager._active_count == 0

    @pytest.mark.asyncio
    async def test_recovery_bypasses_cap(self, manager: SandboxManager) -> None:
        """Recovery replaces a sandbox rather than adding one, so it is never rejected."""
        manager._config.max_active_sandboxes = 1
        created = _wire_creation(manager)

        await manager.create_sandbox("conv-1")
        with pytest.raises(SandboxCapacityError):
            await manager.create_sandbox("conv-2")

        info = await manager.recover_sandbox("conv-1")

        assert info.sandbox_name.startswith("sb-")
        assert len(created) == 2
        assert manager._active_count == 1

    @pytest.mark.asyncio
    async def test_warm_cache_seeds_active_count(self, manager: SandboxManager) -> None:
        claims = [_make_claim("claim-1", "conv-1", "sb-1"), _make_claim("claim-2", "conv-2", "sb-2")]
        manager._k8s.list_sandbox_claims = AsyncMock(return_value=claims)
        manager._k8s.get_sandbox = AsyncMock(
            side_effect=lambda name, namespace: {
                "metadata": {"name": name},
                "status": {"conditions": [{"type": "Ready", "status": "True"}]},
            }
        )

        await manager.warm_cache()

        assert manager._active_count == 2

    @pytest.mark.asyncio
    async def test_warm_cache_excludes_orphans_it_deletes(self, manager: SandboxManager) -> None:
        claims = [_make_claim("claim-1", "conv-1", "sb-1"), _make_claim("claim-orphan", "conv-orphan")]
        manager._k8s.list_sandbox_claims = AsyncMock(return_value=claims)
        manager._k8s.get_sandbox = AsyncMock(
            side_effect=lambda name, namespace: {
                "metadata": {"name": name},
                "status": {"conditions": [{"type": "Ready", "status": "True"}]},
            }
        )
        manager._k8s.delete_sandbox_claim = AsyncMock()

        await manager.warm_cache()

        assert manager._active_count == 1
