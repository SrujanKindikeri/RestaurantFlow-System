# =============================================================================
# RestaurantFlow — Accounts URL Configuration
# Phase 3: Auth + Users + Roles + Permissions + Role Assignments
# =============================================================================

from django.urls import path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)

from .views import (
    # Auth
    RegisterView,
    MeView,
    LogoutView,
    # Users
    UserListCreateView,
    UserDetailView,
    UserDisableView,
    UserReactivateView,
    # Role assignments (nested under user)
    UserRoleListCreateView,
    # Role assignments (standalone)
    UserRoleAssignmentDetailView,
    UserRoleAssignmentDisableView,
    # Roles
    RoleListView,
    RoleDetailView,
    # Permissions
    PermissionListView,
)

urlpatterns = [
    # ------------------------------------------------------------------
    # Authentication
    # ------------------------------------------------------------------
    path("auth/register/", RegisterView.as_view(), name="auth-register"),
    path("auth/login/", TokenObtainPairView.as_view(), name="auth-login"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="auth-token-refresh"),
    path("auth/token/verify/", TokenVerifyView.as_view(), name="auth-token-verify"),
    path("auth/logout/", LogoutView.as_view(), name="auth-logout"),
    path("auth/me/", MeView.as_view(), name="auth-me"),

    # ------------------------------------------------------------------
    # Users
    # ------------------------------------------------------------------
    path("users/", UserListCreateView.as_view(), name="user-list"),
    path("users/<int:pk>/", UserDetailView.as_view(), name="user-detail"),
    path("users/<int:pk>/disable/", UserDisableView.as_view(), name="user-disable"),
    path("users/<int:pk>/reactivate/", UserReactivateView.as_view(), name="user-reactivate"),

    # Role assignments nested under a user
    path("users/<int:pk>/roles/", UserRoleListCreateView.as_view(), name="user-roles"),

    # ------------------------------------------------------------------
    # User role assignments (standalone — for update / disable)
    # ------------------------------------------------------------------
    path(
        "user-role-assignments/<uuid:pk>/",
        UserRoleAssignmentDetailView.as_view(),
        name="user-role-assignment-detail",
    ),
    path(
        "user-role-assignments/<uuid:pk>/disable/",
        UserRoleAssignmentDisableView.as_view(),
        name="user-role-assignment-disable",
    ),

    # ------------------------------------------------------------------
    # Roles
    # ------------------------------------------------------------------
    path("roles/", RoleListView.as_view(), name="role-list"),
    path("roles/<uuid:pk>/", RoleDetailView.as_view(), name="role-detail"),

    # ------------------------------------------------------------------
    # Permissions
    # ------------------------------------------------------------------
    path("permissions/", PermissionListView.as_view(), name="permission-list"),
]
