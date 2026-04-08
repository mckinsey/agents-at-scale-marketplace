"""OpenTelemetry setup for the scheduler."""

import logging
import os

from opentelemetry import trace
from opentelemetry.baggage.propagation import W3CBaggagePropagator
from opentelemetry.propagate import set_global_textmap
from opentelemetry.propagators.composite import CompositePropagator
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

logger = logging.getLogger(__name__)


def setup_otel() -> None:
    """Configure OTEL TracerProvider with W3C TraceContext propagation."""
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    if not endpoint:
        logger.info("OTEL_EXPORTER_OTLP_ENDPOINT not set, tracing disabled")
        return

    try:
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

        resource = Resource.create(
            {
                "service.name": os.getenv("OTEL_SERVICE_NAME", "claude-agent-sdk-scheduler"),
            }
        )
        provider = TracerProvider(resource=resource)
        exporter = OTLPSpanExporter(endpoint=f"{endpoint}/v1/traces")
        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)

        # Set up W3C TraceContext + Baggage propagation
        # Baggage carries ark.session.id from the controller through the scheduler to sandboxes
        propagator = CompositePropagator([TraceContextTextMapPropagator(), W3CBaggagePropagator()])
        set_global_textmap(propagator)

        logger.info("OTEL tracing configured: endpoint=%s", endpoint)
    except Exception:
        logger.exception("Failed to configure OTEL tracing")
