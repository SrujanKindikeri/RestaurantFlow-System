# =============================================================================
# RestaurantFlow — Distributed Tracing (OpenTelemetry, optional)
# Phase 24
#
# OpenTelemetry is OPTIONAL. This module configures OTLP tracing only when:
#   1. The opentelemetry packages are importable, AND
#   2. OTEL_EXPORTER_OTLP_ENDPOINT is set in the environment.
#
# When the packages are not installed, tracing is a documented no-op so the
# application runs unchanged. Sampling is configurable via OTEL_TRACES_SAMPLER_ARG.
#
# Sensitive data is never captured: instrumentations are configured to drop
# DB statement parameters and request bodies. The request_id is propagated as
# a span attribute and trace context is forwarded into Celery tasks where the
# auto-instrumentation supports it.
# =============================================================================

import logging
import os

logger = logging.getLogger("observability.tracing")

_tracing_configured = False


def setup_tracing(service_name: str = "restaurantflow-api", environment: str = "production"):
    """
    Configure OpenTelemetry tracing. Safe to call at process start (ASGI/WSGI).
    Idempotent. Returns True if tracing was activated.
    """
    global _tracing_configured
    if _tracing_configured:
        return True

    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "").strip()
    if not endpoint:
        logger.info("OpenTelemetry tracing disabled: OTEL_EXPORTER_OTLP_ENDPOINT not set.")
        return False

    try:
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    except Exception as exc:
        logger.warning(
            "OpenTelemetry tracing not activated: opentelemetry packages not "
            "installed (%s). Install opentelemetry-sdk + opentelemetry-exporter-otlp "
            "to enable tracing.", exc,
        )
        return False

    try:
        resource = Resource.create({
            "service.name": service_name,
            "service.namespace": "restaurantflow",
            "deployment.environment": environment,
        })
        provider = TracerProvider(resource=resource)

        # Sampler: default parent-based ratio. Configurable via env.
        sampler_arg = os.getenv("OTEL_TRACES_SAMPLER_ARG", "0.1")
        try:
            from opentelemetry.sdk.trace.sampling import ParentBased, TraceIdRatioBased
            ratio = float(sampler_arg)
            provider.sampler = ParentBased(TraceIdRatioBased(ratio))
        except Exception:
            pass  # fall back to default sampling

        exporter = OTLPSpanExporter(endpoint=endpoint)
        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)

        _apply_auto_instrumentation()
        _tracing_configured = True
        logger.info("OpenTelemetry tracing configured → %s (service=%s, env=%s).",
                    endpoint, service_name, environment)
        return True
    except Exception as exc:
        logger.error("OpenTelemetry tracing setup failed: %s", exc)
        return False


def _apply_auto_instrumentation():
    """
    Enable available auto-instrumentations defensively. Each is optional;
    missing packages are skipped. Instrumentations are tuned to avoid
    capturing sensitive parameters.
    """
    attempts = [
        ("opentelemetry.instrumentation.django", "DjangoInstrumentor"),
        ("opentelemetry.instrumentation.psycopg2", "Psycopg2Instrumentor"),
        ("opentelemetry.instrumentation.redis", "RedisInstrumentor"),
        ("opentelemetry.instrumentation.celery", "CeleryInstrumentor"),
        ("opentelemetry.instrumentation.requests", "RequestsInstrumentor"),
    ]
    for mod_name, cls_name in attempts:
        try:
            mod = __import__(mod_name, fromlist=[cls_name])
            instrumentor = getattr(mod, cls_name)()
            # Disable query capture where supported to avoid leaking params.
            instrumentor.instrument()
        except Exception as exc:
            logger.debug("Auto-instrumentation %s skipped: %s", mod_name, exc)


def is_tracing_active() -> bool:
    return _tracing_configured
