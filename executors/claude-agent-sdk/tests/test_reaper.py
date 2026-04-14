"""Tests for annotation-based idle reaper (Tasks 6.3)."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

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


class TestAnnotationReaper:
    @pytest.mark.asyncio
    async def test_expired_claim_deleted(self, manager: SandboxManager) -> None:
        old = datetime.now(timezone.utc) - timedelta(seconds=120)
        claims = [_make_claim("claim-old", "conv-old", last_activity=old)]
        manager._k8s.list_sandbox_claims = AsyncMock(return_value=claims)
        manager._k8s.delete_sandbox_claim = AsyncMock()

        # Run one reaper cycle manually
        manager._config.session_idle_ttl = 60
        now = datetime.now(timezone.utc)
        for item in claims:
            annotations = item["metadata"]["annotations"]
            la_str = annotations.get(ANNOTATION_LAST_ACTIVITY, "")
            la = datetime.fromisoformat(la_str)
            idle = (now - la).total_seconds()
            if idle > 60:
                await manager._k8s.delete_sandbox_claim("claim-old", "test-ns")

        manager._k8s.delete_sandbox_claim.assert_called_once_with("claim-old", "test-ns")

    @pytest.mark.asyncio
    async def test_fresh_claim_not_deleted(self, manager: SandboxManager) -> None:
        fresh = datetime.now(timezone.utc) - timedelta(seconds=10)
        claims = [_make_claim("claim-fresh", "conv-fresh", last_activity=fresh)]
        manager._k8s.list_sandbox_claims = AsyncMock(return_value=claims)
        manager._k8s.delete_sandbox_claim = AsyncMock()

        now = datetime.now(timezone.utc)
        for item in claims:
            la_str = item["metadata"]["annotations"].get(ANNOTATION_LAST_ACTIVITY, "")
            la = datetime.fromisoformat(la_str)
            idle = (now - la).total_seconds()
            if idle > 60:
                await manager._k8s.delete_sandbox_claim("claim-fresh", "test-ns")

        manager._k8s.delete_sandbox_claim.assert_not_called()

    @pytest.mark.asyncio
    async def test_missing_annotation_uses_creation_timestamp(self, manager: SandboxManager) -> None:
        old_created = (datetime.now(timezone.utc) - timedelta(seconds=120)).strftime("%Y-%m-%dT%H:%M:%SZ")
        claims = [_make_claim("claim-no-anno", "conv-no-anno", created=old_created)]
        manager._k8s.list_sandbox_claims = AsyncMock(return_value=claims)
        manager._k8s.delete_sandbox_claim = AsyncMock()

        now = datetime.now(timezone.utc)
        for item in claims:
            la_str = item["metadata"]["annotations"].get(ANNOTATION_LAST_ACTIVITY, "")
            if not la_str:
                created = item["metadata"].get("creationTimestamp", "")
                created_dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                idle = (now - created_dt).total_seconds()
            else:
                idle = 0
            if idle > 60:
                await manager._k8s.delete_sandbox_claim("claim-no-anno", "test-ns")

        manager._k8s.delete_sandbox_claim.assert_called_once_with("claim-no-anno", "test-ns")
