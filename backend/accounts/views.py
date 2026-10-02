# =============================================================================
# RestaurantFlow — Accounts Views
# Phase 3: Auth, Users, Roles, Permissions, Role Assignments
#
# URL layout (registered in accounts/urls.py → config/urls.py):
#
#   POST   /api/auth/register/                   create account (public)
#   POST   /api/auth/login/                      obtain JWT tokens
#   POST   /api/auth/token/refresh/              refresh access token
#   POST   /api/auth/token/verify/               verify token
#   POST   /api/auth/logout/                     blacklist refresh token
#   GET    /api/auth/me/                         current user profile
#
#   GET    /api/users/                           list users (scoped)
#   POST   /api/users/                           create user (admin)
#   GET    /api/users/<id>/                      user detail
#   PATCH  /api/users/<id>/                      update user
#   POST   /api/users/<id>/disable/              soft-disable
#   POST   /api/users/<id>/reactivate/           reactivate
#   GET    /api/users/<id>/roles/                list assignments
#   POST   /api/users/<id>/roles/                create assignment
#
#   GET    /api/roles/                           list all roles
#   GET    /api/roles/<id>/                      role detail
#
#   GET    /api/permissions/                     list all permissions
#
#   GET    /api/user-role-assignments/<id>/      assignment detail
#   PATCH  /api/user-role-assignments/<id>/      update assignment
#   POST   /api/user-role-assignments/<id>/disable/   deactivate
#
# Security:
#   - Never accept is_superuser / is_staff from external input.
#   - privilege_escalation checks in accounts.services / accounts.access.
#   - Resource-not-accessible → 404 (prevents existence leakage).
# =============================================================================

import logging
from django.contrib.auth import get_user_model
from django.db.models import Q
from rest_framework import generics, status
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError

from accounts import access as acl
from accounts import services
from accounts.permissions import (
    HasPermission,
    IsOrganizationAdmin,
    IsRestaurantAdmin,
    IsSelfOrAdmin,
)
from .models import Role, Permission, UserRoleAssignment, UserProfile
from .serializers import (
    UserSerializer,
    UserDetailSerializer,
    UserUpdateSerializer,
    UserCreateSerializer,
    RegisterSerializer,
    RoleSerializer,
    PermissionSerializer,
    UserRoleAssignmentSerializer,
    UserRoleAssignmentCreateSerializer,
)

logger = logging.getLogger("accounts")
User = get_user_model()


# =============================================================================
# Auth views
# =============================================================================

class RegisterView(generics.CreateAPIView):
    """
    POST /api/auth/register/
    Public — create a new user account.
    """
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

    def perform_create(self, serializer):
        user = serializer.save()
        logger.info("New user registered: %s", user.email)


class MeView(APIView):
    """
    GET /api/auth/me/
    Return the currently authenticated user's full profile + scope.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserDetailSerializer(request.user)
        return Response(serializer.data)


class LogoutView(APIView):
    """
    POST /api/auth/logout/
    Blacklist the supplied refresh token, invalidating the session.
    Body: { "refresh": "<refresh_token>" }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            raise ValidationError({"refresh": "Refresh token is required."})

        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except TokenError as exc:
            raise ValidationError({"refresh": str(exc)})

        logger.info("User logged out: %s", request.user.email)
        return Response({"detail": "Successfully logged out."}, status=status.HTTP_200_OK)


# =============================================================================
# User views
# =============================================================================

def _get_user_queryset(request):
    """
    Return a User queryset scoped to what the requesting user can manage.
    Superuser/staff → all users.
    Org admins → users with assignments in their org(s).
    Restaurant admins → users with assignments in their restaurant(s).
    Others → only themselves.
    """
    user = request.user
    if user.is_superuser or user.is_staff:
        return User.objects.select_related("profile").prefetch_related(
            "role_assignments__role",
            "role_assignments__organization",
            "role_assignments__restaurant",
            "role_assignments__branch",
        )

    # Collect org IDs and restaurant IDs accessible to this user
    assignments = user.get_active_assignments()
    org_ids = {a.organization_id for a in assignments if a.organization_id}
    restaurant_ids = {a.restaurant_id for a in assignments if a.restaurant_id}

    # Users who have assignments in any of the actor's accessible orgs/restaurants
    qs = User.objects.filter(
        Q(pk=user.pk) |
        Q(role_assignments__organization_id__in=org_ids, role_assignments__is_active=True) |
        Q(role_assignments__restaurant_id__in=restaurant_ids, role_assignments__is_active=True)
    ).distinct()

    return qs.select_related("profile").prefetch_related(
        "role_assignments__role",
        "role_assignments__organization",
        "role_assignments__restaurant",
        "role_assignments__branch",
    )


class UserListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/users/   — list users (scoped to actor's authority)
    POST /api/users/   — create user (requires user.create permission)
    """

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated(), HasPermission("user.create")()]
        return [IsAuthenticated(), HasPermission("user.view")()]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return UserCreateSerializer
        return UserSerializer

    def get_queryset(self):
        return _get_user_queryset(self.request)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Use the service to enforce privilege-escalation rules
        try:
            user = services.create_user(
                actor=request.user,
                email=serializer.validated_data["email"],
                first_name=serializer.validated_data["first_name"],
                last_name=serializer.validated_data["last_name"],
                phone=serializer.validated_data.get("phone", ""),
                password=serializer.validated_data["password"],
            )
        except PermissionDenied as exc:
            raise PermissionDenied(str(exc))

        out = UserSerializer(user)
        return Response(out.data, status=status.HTTP_201_CREATED)


class UserDetailView(generics.RetrieveUpdateAPIView):
    """
    GET   /api/users/<id>/   — full user detail
    PATCH /api/users/<id>/   — update safe fields
    """
    http_method_names = ["get", "patch", "head", "options"]

    def get_permissions(self):
        if self.request.method == "PATCH":
            return [IsAuthenticated(), IsSelfOrAdmin()]
        return [IsAuthenticated(), IsSelfOrAdmin()]

    def get_serializer_class(self):
        if self.request.method == "PATCH":
            return UserUpdateSerializer
        return UserDetailSerializer

    def get_queryset(self):
        return _get_user_queryset(self.request)

    def get_object(self):
        user_id = self.kwargs["pk"]
        qs = self.get_queryset()

        try:
            obj = qs.get(pk=user_id)
        except User.DoesNotExist:
            raise NotFound("User not found.")

        # Object-level permission check
        self.check_object_permissions(self.request, obj)
        return obj


class UserDisableView(APIView):
    """
    POST /api/users/<pk>/disable/
    Soft-disable a user.
    """
    permission_classes = [IsAuthenticated, HasPermission("user.disable")]

    def post(self, request, pk):
        user = _get_user_or_404(request, pk)
        try:
            services.disable_user(actor=request.user, user=user)
        except (PermissionDenied, ValidationError) as exc:
            raise exc
        return Response(
            {"detail": f"User '{user.email}' has been disabled."},
            status=status.HTTP_200_OK,
        )


class UserReactivateView(APIView):
    """
    POST /api/users/<pk>/reactivate/
    Reactivate a disabled user.
    """
    permission_classes = [IsAuthenticated, HasPermission("user.disable")]

    def post(self, request, pk):
        # fetch without is_active filter for reactivation
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            raise NotFound("User not found.")

        if not acl.can_manage_user(request.user, user):
            if not request.user.is_superuser and not request.user.is_staff:
                raise NotFound("User not found.")

        try:
            services.reactivate_user(actor=request.user, user=user)
        except PermissionDenied as exc:
            raise exc
        return Response(
            {"detail": f"User '{user.email}' has been reactivated."},
            status=status.HTTP_200_OK,
        )


# =============================================================================
# User role assignment views
# =============================================================================

class UserRoleListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/users/<pk>/roles/    — list assignments for a user
    POST /api/users/<pk>/roles/    — create a new assignment
    """
    permission_classes = [IsAuthenticated, HasPermission("role.manage")]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return UserRoleAssignmentCreateSerializer
        return UserRoleAssignmentSerializer

    def _get_target_user(self):
        user_pk = self.kwargs["pk"]
        try:
            target = User.objects.get(pk=user_pk)
        except User.DoesNotExist:
            raise NotFound("User not found.")
        if not acl.can_manage_user(self.request.user, target):
            if not self.request.user.is_superuser and not self.request.user.is_staff:
                raise NotFound("User not found.")
        return target

    def get_queryset(self):
        target = self._get_target_user()
        return UserRoleAssignment.objects.filter(user=target).select_related(
            "role", "organization", "restaurant", "branch"
        )

    def perform_create(self, serializer):
        target = self._get_target_user()

        role = serializer.validated_data["role"]
        organization = serializer.validated_data.get("organization")
        restaurant = serializer.validated_data.get("restaurant")
        branch = serializer.validated_data.get("branch")

        # Privilege-escalation check
        if not acl.can_assign_role(
            self.request.user, role,
            organization=organization,
            restaurant=restaurant,
            branch=branch,
        ):
            if not self.request.user.is_superuser:
                raise PermissionDenied(
                    f"You do not have permission to assign the '{role.code}' role."
                )

        assignment = serializer.save(user=target)
        logger.info(
            "Role assignment created: user=%s role=%s by actor=%s",
            target.email, role.code, self.request.user.email,
        )
        return assignment


class UserRoleAssignmentDetailView(generics.RetrieveUpdateAPIView):
    """
    GET   /api/user-role-assignments/<id>/
    PATCH /api/user-role-assignments/<id>/   — update scope fields
    """
    permission_classes = [IsAuthenticated, HasPermission("role.manage")]
    http_method_names = ["get", "patch", "head", "options"]
    serializer_class = UserRoleAssignmentSerializer

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser or user.is_staff:
            return UserRoleAssignment.objects.select_related(
                "role", "organization", "restaurant", "branch", "user"
            )
        # Limit to assignments for users the actor can manage
        managed_user_ids = _get_user_queryset(self.request).values_list("pk", flat=True)
        return UserRoleAssignment.objects.filter(
            user_id__in=managed_user_ids
        ).select_related("role", "organization", "restaurant", "branch", "user")


class UserRoleAssignmentDisableView(APIView):
    """
    POST /api/user-role-assignments/<pk>/disable/
    Soft-deactivate an assignment.
    """
    permission_classes = [IsAuthenticated, HasPermission("role.manage")]

    def post(self, request, pk):
        try:
            assignment = UserRoleAssignment.objects.select_related("user", "role").get(pk=pk)
        except UserRoleAssignment.DoesNotExist:
            raise NotFound("Assignment not found.")

        if not acl.can_manage_user(request.user, assignment.user):
            if not request.user.is_superuser and not request.user.is_staff:
                raise NotFound("Assignment not found.")

        try:
            services.remove_role_assignment(actor=request.user, assignment=assignment)
        except PermissionDenied as exc:
            raise exc

        return Response(
            {"detail": "Role assignment has been deactivated."},
            status=status.HTTP_200_OK,
        )


# =============================================================================
# Role views
# =============================================================================

class RoleListView(generics.ListAPIView):
    """GET /api/roles/ — list all active roles."""
    permission_classes = [IsAuthenticated, HasPermission("role.view")]
    serializer_class = RoleSerializer

    def get_queryset(self):
        return Role.objects.prefetch_related("permissions").order_by("name")


class RoleDetailView(generics.RetrieveUpdateAPIView):
    """
    GET   /api/roles/<id>/   — role detail
    PATCH /api/roles/<id>/   — update (non-system fields only; admins only)
    """
    http_method_names = ["get", "patch", "head", "options"]

    def get_permissions(self):
        if self.request.method == "PATCH":
            return [IsAuthenticated(), HasPermission("role.manage")()]
        return [IsAuthenticated(), HasPermission("role.view")()]

    serializer_class = RoleSerializer

    def get_queryset(self):
        return Role.objects.prefetch_related("permissions")


# =============================================================================
# Permission views
# =============================================================================

class PermissionListView(generics.ListAPIView):
    """GET /api/permissions/ — list all registered permissions."""
    permission_classes = [IsAuthenticated, HasPermission("permission.view")]
    serializer_class = PermissionSerializer

    def get_queryset(self):
        qs = Permission.objects.all().order_by("module", "action")
        module = self.request.query_params.get("module")
        if module:
            qs = qs.filter(module=module)
        return qs


# =============================================================================
# Internal helpers
# =============================================================================

def _get_user_or_404(request, pk):
    """Fetch a user from the actor-scoped queryset or raise 404."""
    try:
        return _get_user_queryset(request).get(pk=pk)
    except User.DoesNotExist:
        raise NotFound("User not found.")
