"""Tests for sandbox admission control under concurrency."""

import asyncio
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from claude_agent_scheduler.config import SchedulerConfig
from claude_agent_scheduler.sandbox_manager import (
    ANNOTATION_LAST_ACTIVITY,
    LABEL_CONVERSATION_ID,
    LABEL_MANAGED_BY,
    MANAGED_BY_VALUE,
    SandboxCapacityError,
    SandboxManager,
)

API_LATENCY = 0.002


IDLE_TIMESTAMP = "2000-01-01T00:00:00+00:00"


def _make_claim(name: str, conversation_id: str, sandbox_name: str = "") -> dict[str, Any]:
    last_activity = datetime.now(timezone.utc).isoformat()
    claim: dict[str, Any] = {
        "metadata": {
            "name": name,
            "labels": {LABEL_CONVERSATION_ID: conversation_id, LABEL_MANAGED_BY: MANAGED_BY_VALUE},
            "annotations": {ANNOTATION_LAST_ACTIVITY: last_activity},
        },
        "status": {},
    }
    if sandbox_name:
        claim["status"]["sandbox"] = {"name": sandbox_name}
    return claim


@pytest.fixture
def manager() -> SandboxManager:
    config = SchedulerConfig(namespace="test-ns", sandbox_ready_timeout=60)
    with patch("claude_agent_scheduler.sandbox_manager._AsyncK8sHelper"):
        mgr = SandboxManager(config=config)
        mgr._k8s = AsyncMock()
        mgr._seeded = True
        return mgr


def _wire_cluster(manager: SandboxManager) -> list[dict[str, Any]]:
    """Back the mocked K8s helper with a list standing in for the API server's state.

    Creation awaits on both sides of the mutation: a CREATE that returns without
    yielding to the event loop hides races that a real API round-trip exposes.
    """
    live: list[dict[str, Any]] = []

    async def create(
        name: str, template: str, namespace: str, labels: dict[str, str] | None = None
    ) -> dict[str, Any]:
        await asyncio.sleep(API_LATENCY)
        conversation_id = (labels or {}).get(LABEL_CONVERSATION_ID, name)
        live.append(_make_claim(name, conversation_id, f"sb-{name}"))
        await asyncio.sleep(API_LATENCY)
        return {"metadata": {"name": name}}

    async def list_claims(namespace: str, label_selector: str) -> list[dict[str, Any]]:
        await asyncio.sleep(API_LATENCY)
        return list(live)

    async def delete(name: str, namespace: str) -> None:
        live[:] = [c for c in live if c["metadata"]["name"] != name]

    manager._k8s.create_sandbox_claim = create
    manager._k8s.list_sandbox_claims = list_claims
    manager._k8s.delete_sandbox_claim = AsyncMock(side_effect=delete)
    manager._k8s.resolve_sandbox_name = AsyncMock(
        side_effect=lambda claim_name, namespace, timeout: f"sb-{claim_name}"
    )
    manager._k8s.wait_for_sandbox_ready = AsyncMock()
    manager._k8s.get_sandbox_claim = AsyncMock(return_value=None)
    return live


class TestAdmissionControlSeeding:
    @pytest.mark.asyncio
    async def test_creates_are_rejected_until_occupancy_is_seeded(self, manager: SandboxManager) -> None:
        """A bounded scheduler that cannot see current occupancy rejects rather than guesses.

        Regression test: admission stopped LISTing on create, so occupancy came only
        from the startup LIST. When that LIST failed, warm_cache returned with nothing
        seeded and a burst was admitted on top of whatever the cluster already held.
        """
        manager._config.max_active_sandboxes = 3
        manager._seeded = False
        live = _wire_cluster(manager)

        with pytest.raises(SandboxCapacityError):
            await manager.create_sandbox("conv-a")
        assert live == []

        await manager._reconcile_slots(set(), set())
        await manager.create_sandbox("conv-a")
        assert len(live) == 1

    @pytest.mark.asyncio
    async def test_failed_warm_cache_leaves_occupancy_unseeded(self, manager: SandboxManager) -> None:
        """warm_cache must not report a seeded occupancy it never read."""
        from kubernetes_asyncio import client

        manager._config.max_active_sandboxes = 3
        manager._seeded = False
        manager._k8s.list_sandbox_claims = AsyncMock(side_effect=client.ApiException(status=503))

        await manager.warm_cache()

        assert manager._seeded is False

    @pytest.mark.asyncio
    async def test_warm_cache_seeds_occupancy(self, manager: SandboxManager) -> None:
        """A successful startup LIST is what unblocks creates."""
        manager._config.max_active_sandboxes = 3
        manager._seeded = False
        _wire_cluster(manager)

        await manager.warm_cache()

        assert manager._seeded is True
        await manager.create_sandbox("conv-a")

    @pytest.mark.asyncio
    async def test_unlimited_does_not_wait_for_seeding(self, manager: SandboxManager) -> None:
        """With no limit there is nothing to enforce, so occupancy need not be known."""
        manager._config.max_active_sandboxes = 0
        manager._seeded = False
        live = _wire_cluster(manager)

        await manager.create_sandbox("conv-a")

        assert len(live) == 1


class TestAdmissionControlConcurrency:
    @pytest.mark.asyncio
    async def test_cap_holds_under_simultaneous_creates(self, manager: SandboxManager) -> None:
        """A burst of new conversations must not exceed the cap.

        Regression test: the count check used to LIST before creating, so every
        request in a burst read the same stale count and all were admitted.
        """
        manager._config.max_active_sandboxes = 5
        live = _wire_cluster(manager)

        results = await asyncio.gather(
            *[manager.create_sandbox(f"conv-{i}") for i in range(50)], return_exceptions=True
        )

        rejected = [r for r in results if isinstance(r, SandboxCapacityError)]
        unexpected = [
            r for r in results if isinstance(r, Exception) and not isinstance(r, SandboxCapacityError)
        ]
        assert unexpected == []
        assert len(live) == 5
        assert len(rejected) == 45

    @pytest.mark.asyncio
    async def test_zero_means_unlimited(self, manager: SandboxManager) -> None:
        manager._config.max_active_sandboxes = 0
        live = _wire_cluster(manager)

        results = await asyncio.gather(
            *[manager.create_sandbox(f"conv-{i}") for i in range(20)], return_exceptions=True
        )

        assert [r for r in results if isinstance(r, Exception)] == []
        assert len(live) == 20

    @pytest.mark.asyncio
    async def test_reaper_cycle_during_provision_does_not_double_count(
        self, manager: SandboxManager
    ) -> None:
        """A reaper LIST landing between CREATE and readiness must not count the claim twice.

        Regression test: reconciliation used to assign len(claims) onto a counter,
        so a claim seen mid-provision was counted again when the create completed.
        """
        manager._config.max_active_sandboxes = 5
        live = _wire_cluster(manager)
        ready = asyncio.Event()

        async def block(**kwargs: object) -> None:
            await ready.wait()

        manager._k8s.wait_for_sandbox_ready = AsyncMock(side_effect=block)

        task = asyncio.create_task(manager.create_sandbox("conv-1"))
        while not live:
            await asyncio.sleep(0)
        await manager._reap_once()
        assert not task.done()
        ready.set()
        await task

        assert len(live) == 1
        assert len(manager._slots) == 1

    @pytest.mark.asyncio
    async def test_stale_list_does_not_drop_a_concurrent_reservation(
        self, manager: SandboxManager
    ) -> None:
        """Reconciliation must not prune a claim reserved after its LIST was issued."""
        manager._config.max_active_sandboxes = 5
        _wire_cluster(manager)

        reap = asyncio.create_task(manager._reap_once())
        await asyncio.sleep(0)
        await manager.create_sandbox("conv-late")
        await reap

        assert manager._claim_name("conv-late") in manager._slots

    @pytest.mark.asyncio
    async def test_stale_list_does_not_readopt_a_released_claim(self, manager: SandboxManager) -> None:
        """Reconciliation must not resurrect a claim deleted after its LIST was issued.

        Regression test: the adopt side unconditionally unioned the LIST in, so a
        provision that failed and deleted its claim mid-reap had the name put back,
        leaving phantom occupancy that fails closed until the next reaper cycle.
        """
        manager._config.max_active_sandboxes = 2
        live = _wire_cluster(manager)
        list_issued = asyncio.Event()
        reconcile_may_run = asyncio.Event()
        provision_may_fail = asyncio.Event()

        async def list_claims(namespace: str, label_selector: str) -> list[dict[str, Any]]:
            snapshot = list(live)
            list_issued.set()
            await reconcile_may_run.wait()
            return snapshot

        async def wait_ready(**kwargs: object) -> None:
            await provision_may_fail.wait()
            raise TimeoutError("readiness timeout")

        manager._k8s.list_sandbox_claims = list_claims
        manager._k8s.wait_for_sandbox_ready = AsyncMock(side_effect=wait_ready)

        doomed = asyncio.create_task(manager.create_sandbox("conv-doomed"))
        while not live:
            await asyncio.sleep(0)

        reap = asyncio.create_task(manager._reap_once())
        await list_issued.wait()

        provision_may_fail.set()
        with pytest.raises(TimeoutError):
            await doomed

        reconcile_may_run.set()
        await reap

        assert live == []
        assert manager._slots == set()

    @pytest.mark.asyncio
    async def test_capacity_is_reusable_after_reap(self, manager: SandboxManager) -> None:
        """Freeing claims outside the scheduler must free capacity within a reap cycle."""
        manager._config.max_active_sandboxes = 2
        live = _wire_cluster(manager)

        await manager.create_sandbox("conv-1")
        await manager.create_sandbox("conv-2")
        with pytest.raises(SandboxCapacityError):
            await manager.create_sandbox("conv-3")

        live.clear()
        await manager._reap_once()

        assert manager._slots == set()
        await manager.create_sandbox("conv-4")


class TestAdmissionControlAccounting:
    @pytest.mark.asyncio
    async def test_failed_provision_deletes_its_claim_and_frees_capacity(
        self, manager: SandboxManager
    ) -> None:
        """A claim whose sandbox never became ready is deleted, not left holding a slot."""
        manager._config.max_active_sandboxes = 1
        live = _wire_cluster(manager)
        manager._k8s.wait_for_sandbox_ready = AsyncMock(side_effect=TimeoutError("readiness timeout"))

        with pytest.raises(TimeoutError):
            await manager.create_sandbox("conv-doomed")

        assert live == []
        assert manager._slots == set()
        assert manager._in_flight == {}

    @pytest.mark.asyncio
    async def test_adopted_claim_is_not_deleted_on_failure(self, manager: SandboxManager) -> None:
        """A 409 means someone else owns the claim, so a later failure must not delete it."""
        from kubernetes_asyncio import client

        manager._config.max_active_sandboxes = 1
        live = _wire_cluster(manager)
        claim_name = manager._claim_name("conv-adopted")
        live.append(_make_claim(claim_name, "conv-adopted", f"sb-{claim_name}"))
        manager._k8s.create_sandbox_claim = AsyncMock(side_effect=client.ApiException(status=409))
        manager._k8s.wait_for_sandbox_ready = AsyncMock(side_effect=TimeoutError("readiness timeout"))

        with pytest.raises(TimeoutError):
            await manager.create_sandbox("conv-adopted")

        assert [c["metadata"]["name"] for c in live] == [claim_name]
        assert manager._slots == {claim_name}

    @pytest.mark.asyncio
    async def test_create_failure_leaving_no_claim_frees_capacity(self, manager: SandboxManager) -> None:
        """A CREATE that fails outright leaves nothing behind, so its slot must be released."""
        from kubernetes_asyncio import client

        manager._config.max_active_sandboxes = 1
        _wire_cluster(manager)
        working_create = manager._k8s.create_sandbox_claim
        manager._k8s.create_sandbox_claim = AsyncMock(side_effect=client.ApiException(status=500))

        with pytest.raises(client.ApiException):
            await manager.create_sandbox("conv-doomed")

        assert manager._slots == set()

        manager._k8s.create_sandbox_claim = working_create
        await manager.create_sandbox("conv-next")

    @pytest.mark.asyncio
    async def test_concurrent_requests_for_one_conversation_all_failing_free_the_slot(
        self, manager: SandboxManager
    ) -> None:
        """The last request out frees the slot, not the one that happened to take it.

        Regression test: two requests for the same conversation shared a claim name but
        each judged the slot from its own state. The one holding the reservation exited
        while the other was in flight and declined to free it; the other did not believe
        it owned the slot, so a phantom slot survived with nothing left in the cluster.
        """
        from kubernetes_asyncio import client

        manager._config.max_active_sandboxes = 1
        live = _wire_cluster(manager)
        working_create = manager._k8s.create_sandbox_claim

        async def failing_create(
            name: str, template: str, namespace: str, labels: dict[str, str] | None = None
        ) -> dict[str, Any]:
            await asyncio.sleep(API_LATENCY)
            raise client.ApiException(status=500)

        manager._k8s.create_sandbox_claim = failing_create

        results = await asyncio.gather(
            manager.create_sandbox("conv-same"),
            manager.create_sandbox("conv-same"),
            return_exceptions=True,
        )

        assert all(isinstance(r, client.ApiException) for r in results)
        assert live == []
        assert manager._slots == set()
        assert manager._in_flight == {}

        manager._k8s.create_sandbox_claim = working_create
        await manager.create_sandbox("conv-next")

    @pytest.mark.asyncio
    async def test_concurrent_requests_keep_the_slot_when_one_leaves_a_claim(
        self, manager: SandboxManager
    ) -> None:
        """One failure among concurrent requests must not free a slot the other still needs."""
        from kubernetes_asyncio import client

        manager._config.max_active_sandboxes = 1
        live = _wire_cluster(manager)
        working_create = manager._k8s.create_sandbox_claim
        first = True

        async def flaky_create(
            name: str, template: str, namespace: str, labels: dict[str, str] | None = None
        ) -> dict[str, Any]:
            nonlocal first
            await asyncio.sleep(API_LATENCY)
            if first:
                first = False
                raise client.ApiException(status=500)
            return await working_create(name, template, namespace, labels)

        manager._k8s.create_sandbox_claim = flaky_create

        results = await asyncio.gather(
            manager.create_sandbox("conv-same"),
            manager.create_sandbox("conv-same"),
            return_exceptions=True,
        )

        assert len(live) == 1
        assert [isinstance(r, Exception) for r in results].count(False) == 1
        assert manager._slots == {manager._claim_name("conv-same")}

    @pytest.mark.asyncio
    async def test_failed_recovery_frees_the_slot(self, manager: SandboxManager) -> None:
        """A recovery whose recreate leaves no claim must not keep the slot.

        Regression test: recovery deletes the stale claim and re-enters create_sandbox
        with the name still in occupancy, so the recreate reserved nothing. When it
        failed outright the slot stayed held with no claim behind it, and unrelated
        conversations were rejected until the next reaper cycle.
        """
        from kubernetes_asyncio import client

        manager._config.max_active_sandboxes = 1
        live = _wire_cluster(manager)
        working_create = manager._k8s.create_sandbox_claim

        info = await manager.create_sandbox("conv-a")
        assert manager._slots == {info.claim_name}

        async def failing_create(
            name: str, template: str, namespace: str, labels: dict[str, str] | None = None
        ) -> dict[str, Any]:
            await asyncio.sleep(API_LATENCY)
            raise client.ApiException(status=500)

        manager._k8s.create_sandbox_claim = failing_create
        with pytest.raises(client.ApiException):
            await manager.recover_sandbox("conv-a")

        assert live == []
        assert manager._slots == set()

        manager._k8s.create_sandbox_claim = working_create
        await manager.create_sandbox("conv-b")

    @pytest.mark.asyncio
    async def test_last_out_sees_a_discard_by_another_request(self, manager: SandboxManager) -> None:
        """Claim existence is read from shared state, not OR-ed across per-request snapshots.

        Regression test: request A owned the CREATE while B adopted it on 409. B
        finished first reporting a live claim, then A failed and deleted that claim.
        Last-out trusted B's stale snapshot and kept a slot for a claim A had removed.
        """
        from kubernetes_asyncio import client

        manager._config.max_active_sandboxes = 1
        live = _wire_cluster(manager)
        b_gave_up = asyncio.Event()
        a_may_fail = asyncio.Event()
        first = True

        async def create(
            name: str, template: str, namespace: str, labels: dict[str, str] | None = None
        ) -> dict[str, Any]:
            nonlocal first
            if first:
                first = False
                live.append(_make_claim(name, name, f"sb-{name}"))
                await a_may_fail.wait()
                return {"metadata": {"name": name}}
            raise client.ApiException(status=409)

        async def never_ready(claim_name: str, namespace: str, timeout: float) -> str:
            b_gave_up.set()
            raise TimeoutError("sandbox never became ready")

        manager._k8s.create_sandbox_claim = create
        manager._k8s.resolve_sandbox_name = never_ready

        a = asyncio.create_task(manager.create_sandbox("conv-c"))
        await asyncio.sleep(0)
        b = asyncio.create_task(manager.create_sandbox("conv-c"))
        await b_gave_up.wait()
        await asyncio.gather(b, return_exceptions=True)

        assert manager._slots == {manager._claim_name("conv-c")}

        a_may_fail.set()
        await asyncio.gather(a, return_exceptions=True)

        assert live == []
        assert manager._slots == set()

    @pytest.mark.asyncio
    async def test_recovery_reuses_the_same_slot(self, manager: SandboxManager) -> None:
        """Recovery replaces a sandbox rather than adding one, so it is never rejected."""
        manager._config.max_active_sandboxes = 1
        live = _wire_cluster(manager)

        await manager.create_sandbox("conv-1")
        with pytest.raises(SandboxCapacityError):
            await manager.create_sandbox("conv-2")

        info = await manager.recover_sandbox("conv-1")

        assert info.sandbox_name.startswith("sb-")
        assert len(live) == 1
        assert manager._slots == {manager._claim_name("conv-1")}

    @pytest.mark.asyncio
    async def test_recovery_after_reap_does_not_over_admit(self, manager: SandboxManager) -> None:
        """Recovering a claim the reaper already removed must not free someone else's slot.

        Regression test: recovery used to decrement unconditionally, so a claim that
        was already uncounted freed a slot that belonged to another conversation.
        """
        manager._config.max_active_sandboxes = 2
        live = _wire_cluster(manager)

        await manager.create_sandbox("conv-A")
        await manager.create_sandbox("conv-B")

        a_name = manager._claim_name("conv-A")
        for claim in live:
            if claim["metadata"]["name"] == a_name:
                claim["metadata"]["annotations"][ANNOTATION_LAST_ACTIVITY] = IDLE_TIMESTAMP
        await manager._reap_once()

        await manager.recover_sandbox("conv-A")

        assert len(live) == 2
        with pytest.raises(SandboxCapacityError):
            await manager.create_sandbox("conv-C")
        assert len(live) == 2

    @pytest.mark.asyncio
    async def test_warm_cache_seeds_slots(self, manager: SandboxManager) -> None:
        claims = [_make_claim("claim-1", "conv-1", "sb-1"), _make_claim("claim-2", "conv-2", "sb-2")]
        manager._k8s.list_sandbox_claims = AsyncMock(return_value=claims)
        manager._k8s.get_sandbox = AsyncMock(
            side_effect=lambda name, namespace: {
                "metadata": {"name": name},
                "status": {"conditions": [{"type": "Ready", "status": "True"}]},
            }
        )

        await manager.warm_cache()

        assert manager._slots == {"claim-1", "claim-2"}

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

        assert manager._slots == {"claim-1"}
