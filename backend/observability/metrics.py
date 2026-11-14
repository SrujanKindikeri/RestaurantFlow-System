# =============================================================================
# RestaurantFlow — Lightweight Prometheus Metrics Registry
# Phase 24
#
# A self-contained, dependency-free metrics registry that exposes the
# Prometheus text exposition format (version 0.0.4). No external package is
# required, so the metrics endpoint and unit tests work in any environment.
#
# Design choices:
#   - Labels are EXPLICIT and low-cardinality by contract. Callers pass
#     label values; user IDs, order IDs, bill numbers, payment references,
#     raw URLs and raw exception messages are NEVER used as labels.
#   - A hard per-metric cardinality cap drops + warns on runaway label
#     combinations to protect memory in production.
#   - Counter/Gauge/Histogram are thread-safe via a single registry lock.
#   - Histograms emit `_bucket{le=...}` (cumulative), `_sum`, `_count`.
# =============================================================================

import threading
from typing import Iterable, Optional, Sequence, Tuple

from observability.constants import METRIC_CARDINALITY_CAP

import logging

logger = logging.getLogger("observability.metrics")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _escape_label_value(value: str) -> str:
    """Escape a label value per the Prometheus text format."""
    return (
        str(value)
        .replace("\\", "\\\\")
        .replace("\n", "\\n")
        .replace('"', '\\"')
    )


def _label_key(label_names: Sequence[str], label_values: Sequence[str]) -> Tuple[str, ...]:
    return tuple(str(v) for v in label_values)


def _format_labels(label_names: Sequence[str], label_values: Sequence[str], extra: dict = None) -> str:
    """Render `{name="value",...}`. `extra` is appended (used for histogram `le`)."""
    pairs = []
    for name, value in zip(label_names, label_values):
        pairs.append(f'{name}="{_escape_label_value(value)}"')
    if extra:
        for name, value in extra.items():
            pairs.append(f'{name}="{_escape_label_value(value)}"')
    if not pairs:
        return ""
    return "{" + ",".join(pairs) + "}"


# ---------------------------------------------------------------------------
# Metric types
# ---------------------------------------------------------------------------

class _MetricBase:
    metric_type = "untyped"

    def __init__(self, name: str, help: str, label_names: Sequence[str] = ()):
        self.name = name
        self.help = help
        self.label_names = tuple(label_names)
        self._lock = threading.Lock()
        self._values = {}  # label-tuple -> value(s)
        self._cardinality_exceeded = False

    def _validate_labels(self, labels: dict) -> Tuple[str, ...]:
        """Return the label-value tuple, raising on unknown keys."""
        values = []
        for ln in self.label_names:
            if ln not in labels:
                raise KeyError(
                    f"Metric {self.name}: missing required label {ln!r}"
                )
            values.append(labels[ln])
        extra = set(labels) - set(self.label_names)
        if extra:
            raise KeyError(
                f"Metric {self.name}: unexpected labels {sorted(extra)}; "
                f"declared={list(self.label_names)}"
            )
        return tuple(str(v) for v in values)

    def _guard_cardinality(self, key: Tuple[str, ...]) -> bool:
        """Return True if this new key may be recorded."""
        if key in self._values:
            return True
        if len(self._values) >= METRIC_CARDINALITY_CAP:
            if not self._cardinality_exceeded:
                self._cardinality_exceeded = True
                logger.warning(
                    "Metric %s cardinality cap reached (%d); dropping new label "
                    "combination. Review label usage for high-cardinality fields.",
                    self.name, METRIC_CARDINALITY_CAP,
                )
            return False
        return True


class Counter(_MetricBase):
    metric_type = "counter"

    def inc(self, value: float = 1.0, **labels):
        if value < 0:
            raise ValueError(f"Counter {self.name} cannot decrease")
        key = self._validate_labels(labels)
        with self._lock:
            if not self._guard_cardinality(key):
                return
            self._values[key] = self._values.get(key, 0.0) + float(value)

    def get(self, **labels) -> float:
        key = self._validate_labels(labels)
        with self._lock:
            return self._values.get(key, 0.0)

    def _collect(self) -> Iterable[Tuple[str, float]]:
        with self._lock:
            items = list(self._values.items())
        for key, value in items:
            yield f"{self.name}{_format_labels(self.label_names, key)}", value


class Gauge(_MetricBase):
    metric_type = "gauge"

    def set(self, value: float, **labels):
        key = self._validate_labels(labels)
        with self._lock:
            if not self._guard_cardinality(key):
                return
            self._values[key] = float(value)

    def inc(self, value: float = 1.0, **labels):
        key = self._validate_labels(labels)
        with self._lock:
            if not self._guard_cardinality(key):
                return
            self._values[key] = self._values.get(key, 0.0) + float(value)

    def dec(self, value: float = 1.0, **labels):
        self.inc(-float(value), **labels)

    def get(self, **labels) -> float:
        key = self._validate_labels(labels)
        with self._lock:
            return self._values.get(key, 0.0)

    def _collect(self) -> Iterable[Tuple[str, float]]:
        with self._lock:
            items = list(self._values.items())
        for key, value in items:
            yield f"{self.name}{_format_labels(self.label_names, key)}", value


class Histogram(_MetricBase):
    metric_type = "histogram"

    def __init__(self, name: str, help: str, buckets: Sequence[float], label_names: Sequence[str] = ()):
        super().__init__(name, help, label_names)
        self.buckets = tuple(sorted(buckets)) + (float("inf"),)
        # Per key: [bucket_counts list, sum, count]
        self._values = {}

    def observe(self, value: float, **labels):
        value = float(value)
        key = self._validate_labels(labels)
        with self._lock:
            if not self._guard_cardinality(key):
                return
            entry = self._values.get(key)
            if entry is None:
                entry = [[0] * len(self.buckets), 0.0, 0]
                self._values[key] = entry
            bucket_counts, _sum, _count = entry
            for i, le in enumerate(self.buckets):
                if value <= le:
                    bucket_counts[i] += 1
            entry[1] = _sum + value
            entry[2] = _count + 1

    def get_count(self, **labels) -> int:
        key = self._validate_labels(labels)
        with self._lock:
            entry = self._values.get(key)
            return entry[2] if entry else 0

    def get_sum(self, **labels) -> float:
        key = self._validate_labels(labels)
        with self._lock:
            entry = self._values.get(key)
            return entry[1] if entry else 0.0

    def _collect(self):
        with self._lock:
            items = list(self._values.items())
        for key, (bucket_counts, _sum, _count) in items:
            # bucket_counts[i] is already cumulative (observe increments every
            # bucket whose upper bound >= the value). Emit directly.
            for i, le in enumerate(self.buckets):
                le_str = "+Inf" if le == float("inf") else self._fmt_le(le)
                yield (
                    f"{self.name}_bucket{_format_labels(self.label_names, key, extra={'le': le_str})}",
                    bucket_counts[i],
                )
            yield (f"{self.name}_sum{_format_labels(self.label_names, key)}", _sum)
            yield (f"{self.name}_count{_format_labels(self.label_names, key)}", _count)

    @staticmethod
    def _fmt_le(le: float) -> str:
        # Avoid floating noise in labels.
        if le == int(le):
            return str(int(le))
        return repr(le)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

class Registry:
    def __init__(self):
        self._metrics = {}
        self._lock = threading.Lock()

    def register(self, metric: _MetricBase) -> _MetricBase:
        with self._lock:
            if metric.name in self._metrics and self._metrics[metric.name] is not metric:
                raise ValueError(f"Metric already registered: {metric.name}")
            self._metrics[metric.name] = metric
        return metric

    def get(self, name: str) -> Optional[_MetricBase]:
        return self._metrics.get(name)

    def clear(self):
        """Reset all metric values. Intended for tests only."""
        with self._lock:
            for metric in self._metrics.values():
                with metric._lock:
                    metric._values = {}
                    metric._cardinality_exceeded = False

    def render(self) -> str:
        """Render all metrics in Prometheus text exposition format."""
        lines = []
        with self._lock:
            metrics = list(self._metrics.values())
        # Stable ordering by name.
        metrics.sort(key=lambda m: m.name)
        for metric in metrics:
            lines.append(f"# HELP {metric.name} {metric.help}")
            lines.append(f"# TYPE {metric.name} {metric.metric_type}")
            for name_with_labels, value in metric._collect():
                lines.append(f"{name_with_labels} {self._fmt_value(value)}")
        return "\n".join(lines) + ("\n" if lines else "")

    @staticmethod
    def _fmt_value(value: float) -> str:
        if value == float("inf"):
            return "+Inf"
        if value == float("-inf"):
            return "-Inf"
        if isinstance(value, float) and value.is_integer():
            return str(int(value))
        return repr(value)


# ---------------------------------------------------------------------------
# Global registry + declared metrics
# ---------------------------------------------------------------------------

REGISTRY = Registry()

http_requests_total = REGISTRY.register(
    Counter(
        "restaurantflow_http_requests_total",
        "Total HTTP requests by route, method and status class.",
        label_names=("route", "method", "status_class"),
    )
)

http_request_duration_seconds = REGISTRY.register(
    Histogram(
        "restaurantflow_http_request_duration_seconds",
        "HTTP request latency in seconds.",
        buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0),
        label_names=("route", "method"),
    )
)

http_errors_total = REGISTRY.register(
    Counter(
        "restaurantflow_http_errors_total",
        "HTTP responses with status >= 500.",
        label_names=("route", "method"),
    )
)

http_request_size_bytes = REGISTRY.register(
    Histogram(
        "restaurantflow_http_request_size_bytes",
        "HTTP request body size in bytes.",
        buckets=(64, 256, 1024, 4096, 16384, 65536, 262144, 1048576, 10485760),
        label_names=("route", "method"),
    )
)

http_response_size_bytes = REGISTRY.register(
    Histogram(
        "restaurantflow_http_response_size_bytes",
        "HTTP response body size in bytes.",
        buckets=(64, 256, 1024, 4096, 16384, 65536, 262144, 1048576, 10485760),
        label_names=("route", "method"),
    )
)

celery_tasks_total = REGISTRY.register(
    Counter(
        "restaurantflow_celery_tasks_total",
        "Celery tasks started, by name and queue.",
        label_names=("task", "queue"),
    )
)

celery_task_duration_seconds = REGISTRY.register(
    Histogram(
        "restaurantflow_celery_task_duration_seconds",
        "Celery task duration in seconds.",
        buckets=(0.05, 0.1, 0.5, 1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0),
        label_names=("task", "status"),
    )
)

celery_task_failures_total = REGISTRY.register(
    Counter(
        "restaurantflow_celery_task_failures_total",
        "Celery task failures, by task name.",
        label_names=("task",),
    )
)

celery_queue_depth = REGISTRY.register(
    Gauge(
        "restaurantflow_celery_queue_depth",
        "Number of pending messages in a Celery queue.",
        label_names=("queue",),
    )
)

celery_worker_up = REGISTRY.register(
    Gauge(
        "restaurantflow_celery_worker_up",
        "1 if a Celery worker is running, 0 otherwise.",
        label_names=("hostname",),
    )
)

db_connections_in_use = REGISTRY.register(
    Gauge(
        "restaurantflow_db_connections_in_use",
        "Open DB connections in use by Django.",
        label_names=("alias",),
    )
)

db_connections_available = REGISTRY.register(
    Gauge(
        "restaurantflow_db_connections_available",
        "Available DB connection slots reported by the backend.",
        label_names=("alias",),
    )
)

websocket_connections = REGISTRY.register(
    Gauge(
        "restaurantflow_websocket_connections",
        "Active WebSocket consumer connections.",
        label_names=("channel",),
    )
)

websocket_events_total = REGISTRY.register(
    Counter(
        "restaurantflow_websocket_events_total",
        "WebSocket events processed, by channel and event class.",
        label_names=("channel", "event_class"),
    )
)

websocket_errors_total = REGISTRY.register(
    Counter(
        "restaurantflow_websocket_errors_total",
        "WebSocket delivery/processing errors, by channel.",
        label_names=("channel",),
    )
)

business_events_total = REGISTRY.register(
    Counter(
        "restaurantflow_business_events_total",
        "Business-critical operational events, by event identifier.",
        label_names=("event", "severity"),
    )
)

health_check = REGISTRY.register(
    Gauge(
        "restaurantflow_health_check",
        "1 if a dependency health check passes, 0 otherwise.",
        label_names=("component",),
    )
)
