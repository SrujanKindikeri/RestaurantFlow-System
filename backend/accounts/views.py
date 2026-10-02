# =============================================================================
# RestaurantFlow — Accounts Views
# Phase 1 Foundation
# =============================================================================

import logging
from django.contrib.auth import get_user_model
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .serializers import UserSerializer, RegisterSerializer

logger = logging.getLogger("accounts")
User = get_user_model()


class RegisterView(generics.CreateAPIView):
    """
    POST /api/auth/register/
    Create a new user account.
    """

    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    def perform_create(self, serializer):
        user = serializer.save()
        logger.info("New user registered: %s", user.email)


class MeView(APIView):
    """
    GET /api/auth/me/
    Return the currently authenticated user's profile.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)
