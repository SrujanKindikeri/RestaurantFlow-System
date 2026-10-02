# =============================================================================
# RestaurantFlow — Core Views
# =============================================================================

import logging
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status

logger = logging.getLogger("core")


@api_view(["GET"])
@permission_classes([AllowAny])
def health_check(request):
    """
    GET /api/health/

    Public health check endpoint.
    Used by the frontend to verify backend connectivity.

    Response:
        {
            "status": "ok",
            "service": "RestaurantFlow API"
        }
    """
    logger.debug("Health check called.")
    return Response(
        {
            "status": "ok",
            "service": "RestaurantFlow API",
        },
        status=status.HTTP_200_OK,
    )
