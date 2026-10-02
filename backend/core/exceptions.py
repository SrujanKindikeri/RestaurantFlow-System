# =============================================================================
# RestaurantFlow — Custom Exception Handler
# =============================================================================

import logging
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status

logger = logging.getLogger("core")


def custom_exception_handler(exc, context):
    """
    Custom DRF exception handler.
    Wraps all errors in a consistent JSON envelope:

        {
            "error": true,
            "message": "...",
            "details": {...}
        }
    """
    # Call DRF's default handler first
    response = exception_handler(exc, context)

    if response is not None:
        error_data = {
            "error": True,
            "message": _extract_message(response.data),
            "details": response.data,
        }
        response.data = error_data
        logger.warning(
            "API error %s: %s | view=%s",
            response.status_code,
            str(exc),
            context.get("view"),
        )
    else:
        # Unhandled exception — return 500
        logger.error("Unhandled exception: %s | context=%s", str(exc), context, exc_info=True)
        response = Response(
            {
                "error": True,
                "message": "An unexpected server error occurred.",
                "details": None,
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    return response


def _extract_message(data):
    """Extract a human-readable top-level message from DRF error data."""
    if isinstance(data, dict):
        if "detail" in data:
            return str(data["detail"])
        # Return the first field error
        for key, value in data.items():
            if isinstance(value, list) and value:
                return f"{key}: {value[0]}"
        return "Validation error."
    if isinstance(data, list) and data:
        return str(data[0])
    return str(data)
