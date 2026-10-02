# =============================================================================
# RestaurantFlow — Accounts URL Configuration
# =============================================================================

from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView, TokenVerifyView

from .views import RegisterView, MeView

urlpatterns = [
    # Authentication
    path("auth/register/", RegisterView.as_view(), name="auth-register"),
    path("auth/login/", TokenObtainPairView.as_view(), name="auth-login"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="auth-token-refresh"),
    path("auth/token/verify/", TokenVerifyView.as_view(), name="auth-token-verify"),
    # Current user
    path("auth/me/", MeView.as_view(), name="auth-me"),
]
