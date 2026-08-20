"""Tests for ConfigWatcher: initial ConfigMap load and hot-reload watch.

_watch_loop runs `while not self._stop.is_set()`, so every test that enters it
must arrange for the stop event to be set from inside -- otherwise the test
hangs rather than fails. The helpers below set it from the stream generator or
from a patched asyncio.sleep, which is why each loop test terminates.

kubernetes_asyncio is patched at the module level. Note that config.ConfigException
has to be replaced with a real exception class: `except <MagicMock>` is a
TypeError, so leaving it as an auto-created attribute breaks the fallback path
under test rather than exercising it.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from claude_agent_scheduler.config import ConfigWatcher, SchedulerConfig


class _FakeConfigException(Exception):
    """Stands in for kubernetes_asyncio.config.ConfigException."""


def _watcher(**overrides) -> ConfigWatcher:
    return ConfigWatcher(
        configmap_name=overrides.get("name", "scheduler-config"),
        namespace=overrides.get("namespace", "ark-system"),
        config=overrides.get("config", SchedulerConfig()),
    )


def _configmap(data):
    cm = MagicMock()
    cm.data = data
    return cm


def _core_v1_returning(cm):
    """CoreV1Api mock whose read_namespaced_config_map resolves to cm."""
    api = MagicMock()
    api.read_namespaced_config_map = AsyncMock(return_value=cm)
    return api


YAML_RETAIN = "sessionIdleTTL: 42\nshutdownPolicy: Retain\n"


class TestApply:
    def test_mutates_shared_config_in_place(self) -> None:
        """Callers hold a reference to the original config object, so _apply
        must write into it rather than rebind."""
        shared = SchedulerConfig()
        watcher = _watcher(config=shared)

        watcher._apply(SchedulerConfig(session_idle_ttl=99, shutdown_policy="Retain"))

        assert shared.session_idle_ttl == 99
        assert shared.shutdown_policy == "Retain"
        assert watcher.config is shared

    def test_copies_every_field(self) -> None:
        shared = SchedulerConfig()
        watcher = _watcher(config=shared)
        incoming = SchedulerConfig(
            session_idle_ttl=1,
            shutdown_policy="Retain",
            sandbox_ready_timeout=2,
            sandbox_template="other",
            namespace="ns",
            max_active_sandboxes=3,
        )

        watcher._apply(incoming)

        for field_name in SchedulerConfig.model_fields:
            assert getattr(shared, field_name) == getattr(incoming, field_name)


class TestLoadInitial:
    @pytest.mark.asyncio
    async def test_applies_config_from_configmap(self) -> None:
        watcher = _watcher()

        with (
            patch("claude_agent_scheduler.config.config") as k8s_config,
            patch("claude_agent_scheduler.config.client") as k8s_client,
        ):
            k8s_config.ConfigException = _FakeConfigException
            k8s_client.CoreV1Api.return_value = _core_v1_returning(
                _configmap({"config.yaml": YAML_RETAIN})
            )

            await watcher._load_initial()

        assert watcher.config.session_idle_ttl == 42
        assert watcher.config.shutdown_policy == "Retain"

    @pytest.mark.asyncio
    async def test_falls_back_to_kubeconfig_outside_cluster(self) -> None:
        """Running locally there is no service account, so load_kube_config runs."""
        watcher = _watcher()

        with (
            patch("claude_agent_scheduler.config.config") as k8s_config,
            patch("claude_agent_scheduler.config.client") as k8s_client,
        ):
            k8s_config.ConfigException = _FakeConfigException
            k8s_config.load_incluster_config.side_effect = _FakeConfigException()
            k8s_config.load_kube_config = AsyncMock()
            k8s_client.CoreV1Api.return_value = _core_v1_returning(
                _configmap({"config.yaml": YAML_RETAIN})
            )

            await watcher._load_initial()

        k8s_config.load_kube_config.assert_awaited_once()
        assert watcher.config.session_idle_ttl == 42

    @pytest.mark.asyncio
    async def test_configmap_without_config_yaml_keeps_defaults(self) -> None:
        watcher = _watcher()

        with (
            patch("claude_agent_scheduler.config.config") as k8s_config,
            patch("claude_agent_scheduler.config.client") as k8s_client,
        ):
            k8s_config.ConfigException = _FakeConfigException
            k8s_client.CoreV1Api.return_value = _core_v1_returning(_configmap({"other": "x"}))

            await watcher._load_initial()

        assert watcher.config.session_idle_ttl == 1800

    @pytest.mark.asyncio
    async def test_configmap_with_null_data_keeps_defaults(self) -> None:
        """`cm.data or {}` -- a ConfigMap with no data at all reads as None."""
        watcher = _watcher()

        with (
            patch("claude_agent_scheduler.config.config") as k8s_config,
            patch("claude_agent_scheduler.config.client") as k8s_client,
        ):
            k8s_config.ConfigException = _FakeConfigException
            k8s_client.CoreV1Api.return_value = _core_v1_returning(_configmap(None))

            await watcher._load_initial()

        assert watcher.config.session_idle_ttl == 1800

    @pytest.mark.asyncio
    async def test_missing_configmap_is_not_fatal(self) -> None:
        """A scheduler with no ConfigMap must still boot on defaults."""
        watcher = _watcher()

        with (
            patch("claude_agent_scheduler.config.config") as k8s_config,
            patch("claude_agent_scheduler.config.client") as k8s_client,
        ):
            k8s_config.ConfigException = _FakeConfigException
            api = MagicMock()
            api.read_namespaced_config_map = AsyncMock(side_effect=RuntimeError("404"))
            k8s_client.CoreV1Api.return_value = api

            await watcher._load_initial()  # must not raise

        assert watcher.config.session_idle_ttl == 1800


class TestWatchLoop:
    @staticmethod
    def _watch_yielding(events, stop_event):
        """watch.Watch() mock whose stream yields events then sets stop.

        Setting stop after the last event is what lets _watch_loop's `while`
        terminate; without it the loop reconnects forever.
        """
        w = MagicMock()

        async def stream(*_args, **_kwargs):
            for event in events:
                yield event
            stop_event.set()

        w.stream = stream
        w.close = AsyncMock()
        return w

    @pytest.mark.asyncio
    async def test_modified_event_applies_new_config(self) -> None:
        watcher = _watcher()
        event = {"type": "MODIFIED", "object": _configmap({"config.yaml": YAML_RETAIN})}

        with (
            patch("claude_agent_scheduler.config.config") as k8s_config,
            patch("claude_agent_scheduler.config.client"),
            patch("claude_agent_scheduler.config.watch") as k8s_watch,
        ):
            k8s_config.ConfigException = _FakeConfigException
            k8s_watch.Watch.return_value = self._watch_yielding([event], watcher._stop)

            await asyncio.wait_for(watcher._watch_loop(), timeout=5)

        assert watcher.config.session_idle_ttl == 42

    @pytest.mark.asyncio
    async def test_deleted_event_is_ignored(self) -> None:
        """Only ADDED/MODIFIED carry config; DELETED must not wipe it."""
        watcher = _watcher()
        event = {"type": "DELETED", "object": _configmap({"config.yaml": YAML_RETAIN})}

        with (
            patch("claude_agent_scheduler.config.config") as k8s_config,
            patch("claude_agent_scheduler.config.client"),
            patch("claude_agent_scheduler.config.watch") as k8s_watch,
        ):
            k8s_config.ConfigException = _FakeConfigException
            k8s_watch.Watch.return_value = self._watch_yielding([event], watcher._stop)

            await asyncio.wait_for(watcher._watch_loop(), timeout=5)

        assert watcher.config.session_idle_ttl == 1800

    @pytest.mark.asyncio
    async def test_stop_set_mid_stream_breaks_before_applying(self) -> None:
        watcher = _watcher()
        watcher._stop.set()
        event = {"type": "MODIFIED", "object": _configmap({"config.yaml": YAML_RETAIN})}

        with (
            patch("claude_agent_scheduler.config.config") as k8s_config,
            patch("claude_agent_scheduler.config.client"),
            patch("claude_agent_scheduler.config.watch") as k8s_watch,
        ):
            k8s_config.ConfigException = _FakeConfigException
            k8s_watch.Watch.return_value = self._watch_yielding([event], watcher._stop)

            await asyncio.wait_for(watcher._watch_loop(), timeout=5)

        assert watcher.config.session_idle_ttl == 1800

    @pytest.mark.asyncio
    async def test_stream_is_closed_even_when_it_raises(self) -> None:
        """The `finally: await w.close()` must run, or the connection leaks."""
        watcher = _watcher()
        w = MagicMock()

        async def stream(*_args, **_kwargs):
            watcher._stop.set()
            raise RuntimeError("connection reset")
            yield  # pragma: no cover - makes stream an async generator

        w.stream = stream
        w.close = AsyncMock()

        with (
            patch("claude_agent_scheduler.config.config") as k8s_config,
            patch("claude_agent_scheduler.config.client"),
            patch("claude_agent_scheduler.config.watch") as k8s_watch,
            patch("claude_agent_scheduler.config.asyncio.sleep", new=AsyncMock()),
        ):
            k8s_config.ConfigException = _FakeConfigException
            k8s_watch.Watch.return_value = w

            await asyncio.wait_for(watcher._watch_loop(), timeout=5)

        w.close.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_api_error_retries_after_backoff(self) -> None:
        """A failed watch must back off and retry, not kill the scheduler."""
        watcher = _watcher()
        sleep_calls = []

        async def fake_sleep(seconds):
            sleep_calls.append(seconds)
            watcher._stop.set()

        with (
            patch("claude_agent_scheduler.config.config") as k8s_config,
            patch("claude_agent_scheduler.config.client") as k8s_client,
            patch("claude_agent_scheduler.config.asyncio.sleep", new=fake_sleep),
        ):
            k8s_config.ConfigException = _FakeConfigException
            k8s_client.CoreV1Api.side_effect = RuntimeError("api down")

            await asyncio.wait_for(watcher._watch_loop(), timeout=5)

        assert sleep_calls == [5]

    @pytest.mark.asyncio
    async def test_cancellation_propagates(self) -> None:
        """CancelledError is re-raised, not swallowed by the retry handler --
        otherwise stop() could never end the task."""
        watcher = _watcher()

        with (
            patch("claude_agent_scheduler.config.config") as k8s_config,
            patch("claude_agent_scheduler.config.client") as k8s_client,
        ):
            k8s_config.ConfigException = _FakeConfigException
            k8s_client.CoreV1Api.side_effect = asyncio.CancelledError()

            with pytest.raises(asyncio.CancelledError):
                await asyncio.wait_for(watcher._watch_loop(), timeout=5)

    @pytest.mark.asyncio
    async def test_falls_back_to_kubeconfig_outside_cluster(self) -> None:
        """The loop re-resolves credentials on every reconnect, so it carries
        its own copy of the incluster/kubeconfig fallback."""
        watcher = _watcher()
        event = {"type": "ADDED", "object": _configmap({"config.yaml": YAML_RETAIN})}

        with (
            patch("claude_agent_scheduler.config.config") as k8s_config,
            patch("claude_agent_scheduler.config.client"),
            patch("claude_agent_scheduler.config.watch") as k8s_watch,
        ):
            k8s_config.ConfigException = _FakeConfigException
            k8s_config.load_incluster_config.side_effect = _FakeConfigException()
            k8s_config.load_kube_config = AsyncMock()
            k8s_watch.Watch.return_value = self._watch_yielding([event], watcher._stop)

            await asyncio.wait_for(watcher._watch_loop(), timeout=5)

        k8s_config.load_kube_config.assert_awaited()
        assert watcher.config.session_idle_ttl == 42

    @pytest.mark.asyncio
    async def test_stop_between_events_breaks_the_stream(self) -> None:
        """stop() during a live stream must abandon the remaining events
        instead of draining them."""
        watcher = _watcher()
        first = {"type": "MODIFIED", "object": _configmap({"config.yaml": YAML_RETAIN})}
        second = {
            "type": "MODIFIED",
            "object": _configmap({"config.yaml": "sessionIdleTTL: 777\n"}),
        }

        w = MagicMock()

        async def stream(*_args, **_kwargs):
            yield first
            watcher._stop.set()  # arrives before the second event is handled
            yield second

        w.stream = stream
        w.close = AsyncMock()

        with (
            patch("claude_agent_scheduler.config.config") as k8s_config,
            patch("claude_agent_scheduler.config.client"),
            patch("claude_agent_scheduler.config.watch") as k8s_watch,
        ):
            k8s_config.ConfigException = _FakeConfigException
            k8s_watch.Watch.return_value = w

            await asyncio.wait_for(watcher._watch_loop(), timeout=5)

        assert watcher.config.session_idle_ttl == 42  # first applied, second not

class TestStartStop:
    @pytest.mark.asyncio
    async def test_start_loads_then_spawns_watch_task(self) -> None:
        watcher = _watcher()
        started = asyncio.Event()

        async def fake_watch_loop():
            started.set()
            await asyncio.sleep(3600)

        with (
            patch.object(watcher, "_load_initial", new=AsyncMock()) as load_initial,
            patch.object(watcher, "_watch_loop", new=fake_watch_loop),
        ):
            await watcher.start()
            await asyncio.wait_for(started.wait(), timeout=5)

            load_initial.assert_awaited_once()
            assert watcher._task is not None

            await watcher.stop()

    @pytest.mark.asyncio
    async def test_stop_cancels_the_task_and_sets_the_event(self) -> None:
        watcher = _watcher()

        async def fake_watch_loop():
            await asyncio.sleep(3600)

        with (
            patch.object(watcher, "_load_initial", new=AsyncMock()),
            patch.object(watcher, "_watch_loop", new=fake_watch_loop),
        ):
            await watcher.start()
            await watcher.stop()

        assert watcher._stop.is_set()
        assert watcher._task.cancelled() or watcher._task.done()

    @pytest.mark.asyncio
    async def test_stop_without_start_is_safe(self) -> None:
        """stop() guards on self._task, so shutting down a never-started
        watcher must not raise."""
        watcher = _watcher()

        await watcher.stop()

        assert watcher._stop.is_set()
