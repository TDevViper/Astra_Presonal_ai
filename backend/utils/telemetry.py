"""
utils/telemetry.py — OpenTelemetry setup for ASTRA.

Provides:
  - init_telemetry()     call once at startup
  - get_tracer()         returns the module tracer
  - start_span()         context manager for manual spans
  - trace_brain_step()   decorator for Brain pipeline steps

Export targets (via env vars):
  OTEL_ENABLED=true          enable OTel (default: false — zero overhead when off)
  OTEL_EXPORTER_OTLP_ENDPOINT  e.g. http://localhost:4317 (Jaeger/Grafana)
  OTEL_SERVICE_NAME          default: astra
"""

import os
import logging
from contextlib import contextmanager
from functools import wraps
from typing import Optional

logger = logging.getLogger(__name__)

_tracer = None
_enabled = os.getenv("OTEL_ENABLED", "false").lower() == "true"


def init_telemetry(service_name: str = None):
    """Call once at app startup. No-op if OTEL_ENABLED is not set."""
    global _tracer, _enabled

    if not _enabled:
        logger.info("OTel disabled (set OTEL_ENABLED=true to enable)")
        return

    service_name = service_name or os.getenv("OTEL_SERVICE_NAME", "astra")

    try:
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import (
            BatchSpanProcessor,
            ConsoleSpanExporter,
        )
        from opentelemetry.sdk.resources import Resource

        resource = Resource.create({"service.name": service_name})
        provider = TracerProvider(resource=resource)

        # OTLP export (Jaeger / Grafana Tempo / Datadog)
        endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "")
        if endpoint:
            try:
                from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
                    OTLPSpanExporter,
                )

                otlp = OTLPSpanExporter(endpoint=endpoint, insecure=True)
                provider.add_span_processor(BatchSpanProcessor(otlp))
                logger.info("OTel OTLP exporter → %s", endpoint)
            except Exception as e:
                logger.warning(
                    "OTel OTLP exporter failed: %s — falling back to console", e
                )
                provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
        else:
            # No endpoint — log spans to console (useful for local dev)
            provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
            logger.info(
                "OTel console exporter active (set OTEL_EXPORTER_OTLP_ENDPOINT for remote)"
            )

        trace.set_tracer_provider(provider)
        _tracer = trace.get_tracer(service_name)
        logger.info("✅ OpenTelemetry initialized — service=%s", service_name)

    except Exception as e:
        logger.warning("OTel init failed: %s — tracing disabled", e)
        _enabled = False


def get_tracer():
    """Return the OTel tracer, or a no-op stub if disabled."""
    if _tracer:
        return _tracer
    return _NoOpTracer()


@contextmanager
def start_span(name: str, attributes: dict = None):
    """
    Context manager for manual spans.
    Works even if OTel is disabled — no-op in that case.

    Usage:
        with start_span("brain.resolve", {"intent": "general"}):
            result = brain._resolve(...)
    """
    if not _enabled or not _tracer:
        yield None
        return

    try:
        from opentelemetry import trace

        with _tracer.start_as_current_span(name) as span:
            if attributes and span:
                for k, v in attributes.items():
                    span.set_attribute(k, str(v))
            yield span
    except Exception:
        yield None


def get_current_trace_id() -> str:
    """Return current OTel trace ID as hex string, or '-' if none."""
    if not _enabled:
        return "-"
    try:
        from opentelemetry import trace

        ctx = trace.get_current_span().get_span_context()
        if ctx and ctx.is_valid:
            return format(ctx.trace_id, "032x")
    except Exception:
        pass
    return "-"


def instrument_fastapi(app):
    """
    Auto-instrument FastAPI — adds spans for every HTTP request.
    Call after app is created.
    """
    if not _enabled:
        return
    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

        FastAPIInstrumentor.instrument_app(app)
        logger.info("OTel FastAPI instrumentation active")
    except Exception as e:
        logger.warning("OTel FastAPI instrumentation failed: %s", e)


def trace_step(span_name: str = None, attributes: dict = None):
    """
    Decorator — wraps a Brain pipeline method in an OTel span.

    Usage:
        @trace_step("brain.resolve")
        def _resolve(self, user_input, ...):
            ...
    """

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            name = span_name or fn.__qualname__
            with start_span(name, attributes):
                return fn(*args, **kwargs)

        return wrapper

    return decorator


# ── No-op stub (used when OTel is disabled) ───────────────────────────────────


class _NoOpSpan:
    def set_attribute(self, *a, **kw):
        pass

    def set_status(self, *a, **kw):
        pass

    def record_exception(self, *a, **kw):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *a):
        pass


class _NoOpTracer:
    def start_as_current_span(self, *a, **kw):
        return _NoOpSpan()

    def start_span(self, *a, **kw):
        return _NoOpSpan()
