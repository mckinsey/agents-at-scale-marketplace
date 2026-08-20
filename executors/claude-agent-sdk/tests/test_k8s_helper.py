"""Tests for _AsyncK8sHelper, the agent-sandbox CRD boundary.

The rest of the suite patches this class out wholesale, so nothing exercised
the manifests it builds or the not-found handling the reaper depends on.

Two mocking details matter. client.ApiException is replaced with a real
exception class, because `except <MagicMock>` raises TypeError and would mask
the very paths under test. And the timeout tests patch time.monotonic with an
unbounded counter rather than a fixed list: patching the attribute reaches the
real time module, so asyncio's own calls would exhaust a list and surface as
"coroutine raised StopIteration" instead of the timeout being asserted.
"""

import asyncio
import itertools
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from claude_agent_scheduler.sandbox_manager import (
    ANNOTATION_LAST_ACTIVITY,
    CLAIM_API_GROUP,
    CLAIM_API_VERSION,
    CLAIM_PLURAL,
    SANDBOX_API_GROUP,
    SANDBOX_PLURAL,
    _AsyncK8sHelper,
)


class _FakeApiException(Exception):
    """Stands in for kubernetes_asyncio.client.ApiException."""

    def __init__(self, status: int) -> None:
        super().__init__(f"api error {status}")
        self.status = status


class _FakeConfigException(Exception):
    """Stands in for kubernetes_asyncio.config.ConfigException."""


def _ready_helper():
    """A helper that skips real initialization, with its _custom mocked."""
    helper = _AsyncK8sHelper()
    helper._initialized = True
    helper._custom = MagicMock()
    return helper


def _stream_of(*events):
    """watch.Watch() mock whose stream yields the given events then ends.

    The returned mock carries a `consumed` list. Tests that care about *when*
    the code under test stopped reading assert on it -- without that, a
    function that returns on the first event looks identical to one that
    correctly waited for the last.
    """
    w = MagicMock()
    w.consumed = []

    async def stream(*_args, **_kwargs):
        for event in events:
            w.consumed.append(event)
            yield event

    w.stream = stream
    w.close = AsyncMock()
    return w


def _expired_clock():
    """A monotonic() that jumps 100s per call, so any deadline is already past."""
    return itertools.count(0, 100).__next__


def _claim_event(event_type, sandbox_status=None):
    return {"type": event_type, "object": {"status": {"sandbox": sandbox_status or {}}}}


def _sandbox_event(event_type, conditions=None):
    return {"type": event_type, "object": {"status": {"conditions": conditions or []}}}


class TestEnsureInitialized:
    @pytest.mark.asyncio
    async def test_concurrent_callers_initialize_once(self) -> None:
        """Every public method calls this, and the reaper runs alongside live
        requests -- without the double-checked lock they would each build their
        own ApiClient and leak connections."""
        helper = _AsyncK8sHelper()

        with (
            patch("claude_agent_scheduler.sandbox_manager.config") as k8s_config,
            patch("claude_agent_scheduler.sandbox_manager.client") as k8s_client,
        ):
            k8s_config.ConfigException = _FakeConfigException

            await asyncio.gather(*(helper._ensure_initialized() for _ in range(5)))

        assert k8s_client.CustomObjectsApi.call_count == 1
        assert helper._initialized is True

    @pytest.mark.asyncio
    async def test_falls_back_to_kubeconfig_outside_cluster(self) -> None:
        """In-cluster there is a service account; running locally there is not."""
        helper = _AsyncK8sHelper()

        with (
            patch("claude_agent_scheduler.sandbox_manager.config") as k8s_config,
            patch("claude_agent_scheduler.sandbox_manager.client"),
        ):
            k8s_config.ConfigException = _FakeConfigException
            k8s_config.load_incluster_config.side_effect = _FakeConfigException()
            k8s_config.load_kube_config = AsyncMock()

            await helper._ensure_initialized()

        k8s_config.load_kube_config.assert_awaited_once()


class TestCreateSandboxClaim:
    @pytest.mark.asyncio
    async def test_builds_the_claim_manifest(self) -> None:
        """The CRD coordinates and the templateRef are the whole contract with
        agent-sandbox; a wrong group or plural fails at apply time, in cluster."""
        helper = _ready_helper()
        helper._custom.create_namespaced_custom_object = AsyncMock(return_value={"ok": True})

        result = await helper.create_sandbox_claim(
            name="claim-1", template="tmpl", namespace="ns", labels={"a": "b"}
        )

        assert result == {"ok": True}
        kwargs = helper._custom.create_namespaced_custom_object.call_args.kwargs
        assert kwargs["group"] == CLAIM_API_GROUP
        assert kwargs["plural"] == CLAIM_PLURAL
        assert kwargs["namespace"] == "ns"
        manifest = kwargs["body"]
        assert manifest["apiVersion"] == f"{CLAIM_API_GROUP}/{CLAIM_API_VERSION}"
        assert manifest["kind"] == "SandboxClaim"
        assert manifest["metadata"]["name"] == "claim-1"
        assert manifest["metadata"]["labels"] == {"a": "b"}
        assert manifest["spec"]["sandboxTemplateRef"] == {"name": "tmpl"}

    @pytest.mark.asyncio
    async def test_stamps_last_activity_so_the_reaper_does_not_collect_it(self) -> None:
        """_reap_once reads this annotation to decide idleness. A claim created
        without it parses as having no activity, so a brand new sandbox is
        eligible for deletion on the reaper's first pass."""
        helper = _ready_helper()
        helper._custom.create_namespaced_custom_object = AsyncMock(return_value={})

        await helper.create_sandbox_claim(name="c", template="t", namespace="ns")

        manifest = helper._custom.create_namespaced_custom_object.call_args.kwargs["body"]
        assert ANNOTATION_LAST_ACTIVITY in manifest["metadata"]["annotations"]


class TestNotFoundHandling:
    """Both readers turn 404 into None and let everything else through.

    Collapsing 403 or 500 into None is the dangerous version of this code: the
    caller would read "no such sandbox" and cheerfully create a duplicate.
    """

    READERS = [
        ("get_sandbox_claim", "get_namespaced_custom_object"),
        ("get_sandbox", "get_namespaced_custom_object"),
    ]

    @pytest.mark.asyncio
    @pytest.mark.parametrize("method_name,api_method", READERS)
    async def test_404_reads_as_absent(self, method_name, api_method) -> None:
        helper = _ready_helper()
        setattr(helper._custom, api_method, AsyncMock(side_effect=_FakeApiException(404)))

        with patch("claude_agent_scheduler.sandbox_manager.client") as k8s_client:
            k8s_client.ApiException = _FakeApiException
            assert await getattr(helper, method_name)("x", "ns") is None

    @pytest.mark.asyncio
    @pytest.mark.parametrize("method_name,api_method", READERS)
    @pytest.mark.parametrize("status", [403, 500])
    async def test_other_errors_are_not_swallowed(self, method_name, api_method, status) -> None:
        helper = _ready_helper()
        setattr(helper._custom, api_method, AsyncMock(side_effect=_FakeApiException(status)))

        with patch("claude_agent_scheduler.sandbox_manager.client") as k8s_client:
            k8s_client.ApiException = _FakeApiException
            with pytest.raises(_FakeApiException):
                await getattr(helper, method_name)("x", "ns")


class TestPatchClaimAnnotation:
    @pytest.mark.asyncio
    async def test_uses_merge_patch_to_preserve_other_annotations(self) -> None:
        """Merge-patch updates the named keys. A strategic or JSON patch here
        would replace the annotation map and drop whatever else is on the claim."""
        helper = _ready_helper()
        helper._custom.patch_namespaced_custom_object = AsyncMock()

        await helper.patch_claim_annotation("c", "ns", {"k": "v"})

        kwargs = helper._custom.patch_namespaced_custom_object.call_args.kwargs
        assert kwargs["body"] == {"metadata": {"annotations": {"k": "v"}}}
        assert kwargs["_content_type"] == "application/merge-patch+json"


class TestListSandboxClaims:
    @pytest.mark.asyncio
    async def test_filters_by_label_selector(self) -> None:
        """warm_cache and the reaper both rely on this selector to avoid
        touching claims owned by another scheduler."""
        helper = _ready_helper()
        helper._custom.list_namespaced_custom_object = AsyncMock(
            return_value={"items": [{"a": 1}]}
        )

        result = await helper.list_sandbox_claims("ns", "app=x")

        assert result == [{"a": 1}]
        kwargs = helper._custom.list_namespaced_custom_object.call_args.kwargs
        assert kwargs["label_selector"] == "app=x"
        assert kwargs["namespace"] == "ns"


class TestResolveSandboxName:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("status_key", ["name", "Name"])
    async def test_reads_either_capitalisation_of_the_name_field(self, status_key) -> None:
        """The CRD has shipped status.sandbox.name and .Name; dropping either
        branch strands every request on a cluster running the other version."""
        helper = _ready_helper()

        with patch("claude_agent_scheduler.sandbox_manager.watch") as k8s_watch:
            k8s_watch.Watch.return_value = _stream_of(
                _claim_event("ADDED", {status_key: "sbx-1"})
            )
            name = await asyncio.wait_for(
                helper.resolve_sandbox_name("claim-1", "ns", timeout=30), timeout=5
            )

        assert name == "sbx-1"

    @pytest.mark.asyncio
    async def test_waits_past_events_that_carry_no_name_yet(self) -> None:
        """The claim is created before the controller fills in the sandbox, so
        the first events legitimately have an empty status."""
        helper = _ready_helper()

        with patch("claude_agent_scheduler.sandbox_manager.watch") as k8s_watch:
            k8s_watch.Watch.return_value = _stream_of(
                None,
                _claim_event("MODIFIED", {}),
                _claim_event("MODIFIED", {"name": "sbx-3"}),
            )
            name = await asyncio.wait_for(
                helper.resolve_sandbox_name("claim-1", "ns", timeout=30), timeout=5
            )

        assert name == "sbx-3"

    @pytest.mark.asyncio
    async def test_deleted_claim_fails_fast(self) -> None:
        """Without this the resolve would block until timeout on a claim that
        is never coming back."""
        helper = _ready_helper()

        with patch("claude_agent_scheduler.sandbox_manager.watch") as k8s_watch:
            k8s_watch.Watch.return_value = _stream_of(_claim_event("DELETED"))
            with pytest.raises(RuntimeError, match="deleted while resolving"):
                await asyncio.wait_for(
                    helper.resolve_sandbox_name("claim-1", "ns", timeout=30), timeout=5
                )

    @pytest.mark.asyncio
    async def test_times_out(self) -> None:
        helper = _ready_helper()

        with (
            patch("claude_agent_scheduler.sandbox_manager.watch"),
            patch(
                "claude_agent_scheduler.sandbox_manager.time.monotonic",
                side_effect=_expired_clock(),
            ),
        ):
            with pytest.raises(TimeoutError, match="Could not resolve sandbox name"):
                await asyncio.wait_for(
                    helper.resolve_sandbox_name("claim-1", "ns", timeout=10), timeout=5
                )

    @pytest.mark.asyncio
    async def test_closes_the_watch_even_when_the_stream_raises(self) -> None:
        """The watch holds an HTTP connection; the finally is what keeps a
        failed resolve from leaking one per attempt."""
        helper = _ready_helper()
        w = MagicMock()

        async def stream(*_args, **_kwargs):
            raise RuntimeError("connection reset")
            yield  # pragma: no cover - makes stream an async generator

        w.stream = stream
        w.close = AsyncMock()

        with patch("claude_agent_scheduler.sandbox_manager.watch") as k8s_watch:
            k8s_watch.Watch.return_value = w
            with pytest.raises(RuntimeError):
                await asyncio.wait_for(
                    helper.resolve_sandbox_name("claim-1", "ns", timeout=30), timeout=5
                )

        w.close.assert_awaited_once()


class TestWaitForSandboxReady:
    @pytest.mark.asyncio
    async def test_returns_only_once_ready_is_true(self) -> None:
        """Ready=False and unrelated condition types must not be mistaken for
        readiness -- returning early hands the caller a sandbox that refuses
        connections."""
        helper = _ready_helper()
        w = _stream_of(
            _sandbox_event("MODIFIED", [{"type": "Ready", "status": "False"}]),
            _sandbox_event("MODIFIED", [{"type": "Scheduled", "status": "True"}]),
            _sandbox_event("MODIFIED", [{"type": "Ready", "status": "True"}]),
        )

        with patch("claude_agent_scheduler.sandbox_manager.watch") as k8s_watch:
            k8s_watch.Watch.return_value = w
            await asyncio.wait_for(
                helper.wait_for_sandbox_ready("sbx", "ns", timeout=30), timeout=5
            )

        # Returning on either of the first two events would leave the stream
        # only partly read -- that is the assertion, not the bare return.
        assert len(w.consumed) == 3

    @pytest.mark.asyncio
    async def test_deleted_sandbox_fails_fast(self) -> None:
        helper = _ready_helper()

        with patch("claude_agent_scheduler.sandbox_manager.watch") as k8s_watch:
            k8s_watch.Watch.return_value = _stream_of(_sandbox_event("DELETED"))
            with pytest.raises(RuntimeError, match="deleted before becoming ready"):
                await asyncio.wait_for(
                    helper.wait_for_sandbox_ready("sbx", "ns", timeout=30), timeout=5
                )

    @pytest.mark.asyncio
    async def test_times_out(self) -> None:
        helper = _ready_helper()

        with (
            patch("claude_agent_scheduler.sandbox_manager.watch"),
            patch(
                "claude_agent_scheduler.sandbox_manager.time.monotonic",
                side_effect=_expired_clock(),
            ),
        ):
            with pytest.raises(TimeoutError, match="did not become ready"):
                await asyncio.wait_for(
                    helper.wait_for_sandbox_ready("sbx", "ns", timeout=10), timeout=5
                )

    @pytest.mark.asyncio
    async def test_watches_the_sandbox_crd_not_the_claim(self) -> None:
        """This class talks to two different CRDs in two different API groups.
        Watching the claim here would wait for a Ready condition that the claim
        never publishes, so readiness would only ever end in a timeout."""
        helper = _ready_helper()
        captured = {}
        w = MagicMock()

        async def stream(*_args, **kwargs):
            captured.update(kwargs)
            yield _sandbox_event("MODIFIED", [{"type": "Ready", "status": "True"}])

        w.stream = stream
        w.close = AsyncMock()

        with patch("claude_agent_scheduler.sandbox_manager.watch") as k8s_watch:
            k8s_watch.Watch.return_value = w
            await asyncio.wait_for(
                helper.wait_for_sandbox_ready("sbx", "ns", timeout=30), timeout=5
            )

        assert captured["group"] == SANDBOX_API_GROUP
        assert captured["plural"] == SANDBOX_PLURAL
        assert captured["field_selector"] == "metadata.name=sbx"


class TestDeleteSandboxClaim:
    @pytest.mark.asyncio
    async def test_already_deleted_is_success(self) -> None:
        """The reaper and a shutdown can both delete the same claim; treating
        404 as failure would turn a routine race into a logged error."""
        helper = _ready_helper()
        helper._custom.delete_namespaced_custom_object = AsyncMock(
            side_effect=_FakeApiException(404)
        )

        with patch("claude_agent_scheduler.sandbox_manager.client") as k8s_client:
            k8s_client.ApiException = _FakeApiException
            await helper.delete_sandbox_claim("c", "ns")  # must not raise

    @pytest.mark.asyncio
    async def test_real_failure_propagates(self) -> None:
        """A 500 swallowed here leaks the sandbox: nothing else retries."""
        helper = _ready_helper()
        helper._custom.delete_namespaced_custom_object = AsyncMock(
            side_effect=_FakeApiException(500)
        )

        with patch("claude_agent_scheduler.sandbox_manager.client") as k8s_client:
            k8s_client.ApiException = _FakeApiException
            with pytest.raises(_FakeApiException):
                await helper.delete_sandbox_claim("c", "ns")


class TestClose:
    @pytest.mark.asyncio
    async def test_close_releases_the_client_and_allows_reinit(self) -> None:
        """Resetting _initialized is what lets a reconnect rebuild the client;
        leaving it True would keep a closed ApiClient in place forever."""
        helper = _ready_helper()
        helper._api_client = AsyncMock()

        await helper.close()

        assert helper._api_client is None
        assert helper._initialized is False
