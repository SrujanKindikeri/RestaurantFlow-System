# =============================================================================
# RestaurantFlow — Observability App
# Phase 24: Monitoring, logging, metrics, tracing, and alerting integration.
#
# This app provides production-grade observability WITHOUT duplicating the
# existing Phase 15 Central Control alert engine or the Phase 16 Notification
# delivery center. Metric-based alerts raised by Alertmanager are forwarded
# into CentralAlert via the existing deduplication/lifecycle machinery.
# =============================================================================

default_app_config = "observability.apps.ObservabilityConfig"
