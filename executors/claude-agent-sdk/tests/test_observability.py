"""Tests for scheduler OTEL setup.

setup_otel() mutates process-global state, and OTEL ignores a second
set_tracer_provider call, so every test patches the sinks instead of letting
the real ones run -- otherwise the first test would disable all the others.
"""

from unittest.mock import patch

import pytest

from claude_agent_scheduler.observability import setup_otel


@pytest.fixture
def otel_sinks():
    """Patch the two global sinks and the exporter, yielding the mocks."""
    with (
        patch("claude_agent_scheduler.observability.trace.set_tracer_provider") as set_provider,
        patch("claude_agent_scheduler.observability.set_global_textmap") as set_textmap,
        patch(
            "opentelemetry.exporter.otlp.proto.http.trace_exporter.OTLPSpanExporter"
        ) as exporter,
    ):
        yield {"set_provider": set_provider, "set_textmap": set_textmap, "exporter": exporter}


class TestSetupOtelDisabled:
    def test_no_endpoint_is_a_no_op(self, monkeypatch, otel_sinks) -> None:
        """Tracing is opt-in: without the endpoint nothing global is touched."""
        monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)

        setup_otel()

        otel_sinks["set_provider"].assert_not_called()
        otel_sinks["set_textmap"].assert_not_called()

    def test_empty_endpoint_is_a_no_op(self, monkeypatch, otel_sinks) -> None:
        """An empty env var is as good as unset, not an endpoint of ""."""
        monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "")

        setup_otel()

        otel_sinks["set_provider"].assert_not_called()


class TestSetupOtelEnabled:
    def test_appends_v1_traces_to_endpoint(self, monkeypatch, otel_sinks) -> None:
        """The env var carries the collector root; the signal path is added here."""
        monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://collector:4318")

        setup_otel()

        otel_sinks["exporter"].assert_called_once_with(
            endpoint="http://collector:4318/v1/traces"
        )

    def test_propagator_carries_tracecontext_and_baggage(self, monkeypatch, otel_sinks) -> None:
        """Baggage is not optional: ark.session.id rides it from controller to sandbox."""
        monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://collector:4318")

        setup_otel()

        composite = otel_sinks["set_textmap"].call_args.args[0]
        # Assert the wire contract, not which classes were assembled: fields is
        # the public union of every propagator's header names, so swapping an
        # implementation that still emits the header is not a regression.
        assert composite.fields >= {"traceparent", "baggage"}

    @pytest.mark.parametrize(
        "env_value,expected",
        [(None, "claude-agent-sdk-scheduler"), ("custom-scheduler", "custom-scheduler")],
    )
    def test_service_name(self, monkeypatch, otel_sinks, env_value, expected) -> None:
        """Traces from every scheduler would collapse into one service in the
        backend if the resource attribute were dropped."""
        monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://collector:4318")
        if env_value is None:
            monkeypatch.delenv("OTEL_SERVICE_NAME", raising=False)
        else:
            monkeypatch.setenv("OTEL_SERVICE_NAME", env_value)

        setup_otel()

        provider = otel_sinks["set_provider"].call_args.args[0]
        assert provider.resource.attributes["service.name"] == expected


class TestSetupOtelFailure:
    def test_broken_telemetry_does_not_stop_the_scheduler(self, monkeypatch, otel_sinks) -> None:
        """setup_otel runs during boot. An unreachable or malformed collector
        must degrade to no tracing, not to a scheduler that will not start."""
        monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://collector:4318")
        otel_sinks["exporter"].side_effect = RuntimeError("bad endpoint")

        setup_otel()  # must not raise

        otel_sinks["set_provider"].assert_not_called()
