"""Tests for the reaper — calls _reap_once directly against the real code."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, call, patch

import pytest

from claude_agent_scheduler.config import SchedulerConfig
from claude_agent_scheduler.sandbox_manager import (
    ANNOTATION_LAST_ACTIVITY,
    LABEL_CONVERSATION_ID,
    LABEL_MANAGED_BY,
    MANAGED_BY_VALUE,
    SandboxManager,
)


def _make_claim(
    name: str, conversation_id: str, last_activity: datetime | None = None, created: str = ""
) -> dict:  # type: ignore[type-arg]
    annotations: dict[str, str] = {}
    if last_activity:
        annotations[ANNOTATION_LAST_ACTIVITY] = last_activity.isoformat()
    metadata: dict = {  # type: ignore[type-arg]
        "name": name,
        "labels": {LABEL_CONVERSATION_ID: conversation_id, LABEL_MANAGED_BY: MANAGED_BY_VALUE},
        "annotations": annotations,
    }
    if created:
        metadata["creationTimestamp"] = created
    return {"metadata": metadata, "status": {}}


@pytest.fixture
def config() -> SchedulerConfig:
    return SchedulerConfig(session_idle_ttl=60, namespace="test-ns")


@pytest.fixture
def manager(config: SchedulerConfig) -> SandboxManager:
    with patch("claude_agent_scheduler.sandbox_manager._AsyncK8sHelper"):
        mgr = SandboxManager(config=config)
        mgr._k8s = AsyncMock()
        return mgr


class TestReapOnce:
    @pytest.mark.asyncio
    async def test_expired_claim_deleted(self, manager: SandboxManager) -> None:
        old = datetime.now(timezone.utc) - timedelta(seconds=120)
        claims = [_make_claim("claim-old", "conv-old", last_activity=old)]
        manager._k8s.list_sandbox_claims = AsyncMock(return_value=claims)
        manager._k8s.delete_sandbox_claim = AsyncMock()

        await manager._reap_once()

        manager._k8s.delete_sandbox_claim.assert_called_once_with("claim-old", "test-ns")

    @pytest.mark.asyncio
    async def test_expired_claim_with_retain_policy_not_deleted(self, manager: SandboxManager) -> None:
        old = datetime.now(timezone.utc) - timedelta(seconds=120)
        claims = [_make_claim("claim-retain", "conv-retain", last_activity=old)]
        manager._k8s.list_sandbox_claims = AsyncMock(return_value=claims)
        manager._k8s.delete_sandbox_claim = AsyncMock()
        manager._config.shutdown_policy = "Retain"

        await manager._reap_once()

        manager._k8s.delete_sandbox_claim.assert_not_called()

    @pytest.mark.asyncio
    async def test_expired_claim_evicts_cache(self, manager: SandboxManager) -> None:
        from claude_agent_scheduler.sandbox_manager import SandboxInfo

        old = datetime.now(timezone.utc) - timedelta(seconds=120)
        claims = [_make_claim("claim-cached", "conv-cached", last_activity=old)]
        manager._k8s.list_sandbox_claims = AsyncMock(return_value=claims)
        manager._k8s.delete_sandbox_claim = AsyncMock()

        # Pre-populate cache
        info = SandboxInfo(claim_name="claim-cached", sandbox_name="sb-cached", service_fqdn="sb-cached.test-ns.svc.cluster.local")
        manager._cache.put("conv-cached", info)
        assert manager._cache.get("conv-cached") is not None

        await manager._reap_once()

        assert manager._cache.get("conv-cached") is None

    @pytest.mark.asyncio
    async def test_fresh_claim_not_deleted(self, manager: SandboxManager) -> None:
        fresh = datetime.now(timezone.utc) - timedelta(seconds=10)
        claims = [_make_claim("claim-fresh", "conv-fresh", last_activity=fresh)]
        manager._k8s.list_sandbox_claims = AsyncMock(return_value=claims)
        manager._k8s.delete_sandbox_claim = AsyncMock()

        await manager._reap_once()

        manager._k8s.delete_sandbox_claim.assert_not_called()

    @pytest.mark.asyncio
    async def test_missing_annotation_uses_creation_timestamp(self, manager: SandboxManager) -> None:
        old_created = (datetime.now(timezone.utc) - timedelta(seconds=120)).strftime("%Y-%m-%dT%H:%M:%SZ")
        claims = [_make_claim("claim-no-anno", "conv-no-anno", created=old_created)]
        manager._k8s.list_sandbox_claims = AsyncMock(return_value=claims)
        manager._k8s.delete_sandbox_claim = AsyncMock()

        await manager._reap_once()

        manager._k8s.delete_sandbox_claim.assert_called_once_with("claim-no-anno", "test-ns")

    @pytest.mark.asyncio
    async def test_unparseable_annotation_treated_as_expired(self, manager: SandboxManager) -> None:
        claims = [_make_claim("claim-bad-ts", "conv-bad-ts")]
        claims[0]["metadata"]["annotations"][ANNOTATION_LAST_ACTIVITY] = "not-a-timestamp"
        manager._k8s.list_sandbox_claims = AsyncMock(return_value=claims)
        manager._k8s.delete_sandbox_claim = AsyncMock()

        await manager._reap_once()

        manager._k8s.delete_sandbox_claim.assert_called_once_with("claim-bad-ts", "test-ns")

    @pytest.mark.asyncio
    async def test_label_selector_passed_to_list(self, manager: SandboxManager) -> None:
        manager._k8s.list_sandbox_claims = AsyncMock(return_value=[])

        await manager._reap_once()

        manager._k8s.list_sandbox_claims.assert_called_once_with(
            "test-ns", f"{LABEL_MANAGED_BY}={MANAGED_BY_VALUE}"
        )

    @pytest.mark.asyncio
    async def test_evict_before_delete_ordering(self, manager: SandboxManager) -> None:
        """Cache eviction must happen before claim deletion."""
        from claude_agent_scheduler.sandbox_manager import SandboxInfo

        old = datetime.now(timezone.utc) - timedelta(seconds=120)
        claims = [_make_claim("claim-order", "conv-order", last_activity=old)]
        manager._k8s.list_sandbox_claims = AsyncMock(return_value=claims)

        # Track call order
        call_order: list[str] = []
        original_evict = manager._cache.evict

        def tracking_evict(cid: str) -> None:
            call_order.append("evict")
            original_evict(cid)

        async def tracking_delete(name: str, ns: str) -> None:
            call_order.append("delete")

        manager._cache.evict = tracking_evict  # type: ignore[assignment]
        manager._k8s.delete_sandbox_claim = tracking_delete  # type: ignore[assignment]

        await manager._reap_once()

        assert call_order == ["evict", "delete"]
