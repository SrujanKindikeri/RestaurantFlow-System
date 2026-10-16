# =============================================================================
# RestaurantFlow — Enterprise Signals
# Phase 20
#
# Signal handlers for the enterprise app.
# Registered via apps.py EnterpriseConfig.ready().
# =============================================================================

import logging

logger = logging.getLogger("enterprise")

# Signal handlers are added here as the app grows.
# Currently the enterprise app does not require model-level signals —
# all side effects are orchestrated through service functions which
# use explicit function calls rather than implicit signals.
# This file must exist because apps.py imports it.
