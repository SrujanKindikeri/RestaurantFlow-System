# =============================================================================
# RestaurantFlow — WebSocket Observability Helpers
# Phase 24
#
# Thin, async-safe wrappers around the WS metrics. Channels consumers call
# these from connect/disconnect/receive. They never raise and never record
# message payloads or user/tenant identifiers as labels.
# =============================================================================

import logging

from observability.metrics import (
    websocket_connections,
    websocket_events_total,
    websocket_errors_total,
)

logger = logging.getLogger("observability.ws")


def ws_connect(channel: str) -> None:
    try:
        websocket_connections.inc(channel=channel or "unknown")
    except Exception as exc:
        logger.debug("ws_connect metric failed: %s", exc)


def ws_disconnect(channel: str) -> None:
    try:
        websocket_connections.dec(channel=channel or "unknown")
    except Exception as exc:
        logger.debug("ws_disconnect metric failed: %s", exc)


def ws_event(channel: str, event_class: str = "message") -> None:
    try:
        websocket_events_total.inc(channel=channel or "unknown", event_class=event_class or "message")
    except Exception as exc:
        logger.debug("ws_event metric failed: %s", exc)


def ws_error(channel: str) -> None:
    try:
        websocket_errors_total.inc(channel=channel or "unknown")
    except Exception as exc:
        logger.debug("ws_error metric failed: %s", exc)
