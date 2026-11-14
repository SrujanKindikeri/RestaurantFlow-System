# =============================================================================
# RestaurantFlow — Celery Observability Signals
# Phase 24
#
# Wires Celery signals to the metrics registry and the structured-log
# context. Task arguments are NEVER recorded as labels. The request_id is
# propagated from the calling request into the task context when present so
# background-task logs share a correlation id with the originating request.
#
# All handlers are defensive: an exception inside instrumentation is logged
# and swallowed so it never affects task execution.
# =============================================================================

import logging
import threading
import time

logger = logging.getLogger("observability.celery")

# task_id -> monotonic start time
_start_times = {}
_start_lock = threading.Lock()


def _queue_from_task(task) -> str:
    try:
        delivery = getattr(task.request, "delivery_info", None) or {}
        rk = delivery.get("routing_key") if delivery else None
        return rk or "default"
    except Exception:
        return "default"


def _request_id_from_task(task):
    """Best-effort extraction of a propagated request_id from task headers."""
    try:
        headers = getattr(task.request, "headers", None) or {}
        rid = headers.get("request_id")
        if rid:
            return rid
        # Some celery versions expose custom properties on the request directly.
        rid = getattr(task.request, "request_id", None)
        return rid
    except Exception:
        return None


def _connect():
    """Connect signal receivers. Imported lazily; idempotent."""
    try:
        from celery.signals import (
            task_prerun,
            task_postrun,
            task_failure,
            worker_ready,
            worker_shutdown,
        )
    except Exception as exc:  # celery not installed / not available
        logger.debug("Celery signals unavailable: %s", exc)
        return

    from observability.metrics import (
        celery_tasks_total,
        celery_task_duration_seconds,
        celery_task_failures_total,
        celery_worker_up,
    )
    from observability.context import LogContext, set_context

    @task_prerun.connect
    def _on_task_prerun(sender=None, task_id=None, task=None, **kwargs):
        try:
            name = getattr(sender, "name", None) or "unknown"
            queue = _queue_from_task(task) if task is not None else "default"
            celery_tasks_total.inc(task=name, queue=queue)
            with _start_lock:
                _start_times[task_id] = time.perf_counter()
            rid = _request_id_from_task(task) if task is not None else None
            if rid:
                set_context(LogContext(request_id=rid))
        except Exception as exc:
            logger.debug("task_prerun instrumentation failed: %s", exc)

    @task_postrun.connect
    def _on_task_postrun(sender=None, task_id=None, task=None, retval=None, state=None, **kwargs):
        try:
            name = getattr(sender, "name", None) or "unknown"
            with _start_lock:
                start = _start_times.pop(task_id, None)
            duration = max(time.perf_counter() - start, 0.0) if start is not None else 0.0
            status = (state or "unknown").lower()
            celery_task_duration_seconds.observe(duration, task=name, status=status)
        except Exception as exc:
            logger.debug("task_postrun instrumentation failed: %s", exc)

    @task_failure.connect
    def _on_task_failure(sender=None, task_id=None, exception=None, **kwargs):
        try:
            name = getattr(sender, "name", None) or "unknown"
            celery_task_failures_total.inc(task=name)
        except Exception as exc:
            logger.debug("task_failure instrumentation failed: %s", exc)

    @worker_ready.connect
    def _on_worker_ready(sender=None, **kwargs):
        try:
            hostname = sender or "worker"
            celery_worker_up.set(1, hostname=hostname)
        except Exception as exc:
            logger.debug("worker_ready instrumentation failed: %s", exc)

    @worker_shutdown.connect
    def _on_worker_shutdown(sender=None, **kwargs):
        try:
            hostname = sender or "worker"
            celery_worker_up.set(0, hostname=hostname)
        except Exception as exc:
            logger.debug("worker_shutdown instrumentation failed: %s", exc)


# Connect at import time (apps.ready imports this module).
_connect()


def update_queue_depths():
    """
    Update the celery_queue_depth gauge for each configured queue by
    inspecting the Redis broker. Safe to call from a periodic task. No-op
    outside a real Celery/Redis environment.
    """
    try:
        from celery import current_app
        from observability.metrics import celery_queue_depth
        with current_app.connection_or_acquire() as conn:
            client = conn.channel().client  # redis client when using redis broker
            for queue in _configured_queues():
                try:
                    depth = client.llen(queue)
                except Exception:
                    depth = 0
                celery_queue_depth.set(int(depth or 0), queue=queue)
    except Exception as exc:
        logger.debug("update_queue_depths failed: %s", exc)


def _configured_queues():
    try:
        from django.conf import settings
        routes = getattr(settings, "CELERY_TASK_ROUTES", {}) or {}
        queues = {"default"}
        for spec in routes.values():
            if isinstance(spec, dict) and "queue" in spec:
                queues.add(spec["queue"])
        return queues
    except Exception:
        return {"default"}
