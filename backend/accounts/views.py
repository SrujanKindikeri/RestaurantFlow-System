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
from django.contrib.auth import get_user_model, authenticate
from django.db.models import Q
from rest_framework import generics, status
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from accounts import access as acl
from accounts import services
from accounts.permissions import (
    HasPermission,
    IsOrganizationAdmin,
    IsRestaurantAdmin,
    IsSelfOrAdmin,
)
from core.security import (
    record_security_event,
    record_login_failure,
    is_login_locked_out,
    clear_login_failures,
    revoke_user_sessions,
)
from core.throttles import (
    LoginRateThrottle,
    RegistrationRateThrottle,
    PasswordResetRateThrottle,
)
from .models import Role, Permission, UserRoleAssignment, UserProfile, SecurityAuditLog
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
    PasswordChangeSerializer,
    SecurityAuditLogSerializer,
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

    Rate-limited via RegistrationRateThrottle to prevent account-spam attacks.
    """
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]
    throttle_classes = [RegistrationRateThrottle]

    def perform_create(self, serializer):
        user = serializer.save()
        logger.info("New user registered: %s", user.email)
        record_security_event(
            event=SecurityAuditLog.EVENT_USER_REGISTERED,
            actor=user,
            target_user=user,
            ip_address=self._get_client_ip(),
            user_agent=self._get_user_agent(),
            metadata={"email": user.email},
        )

    def _get_client_ip(self):
        xff = self.request.META.get("HTTP_X_FORWARDED_FOR")
        if xff:
            return xff.split(",")[0].strip()
        return self.request.META.get("REMOTE_ADDR")

    def _get_user_agent(self):
        return self.request.META.get("HTTP_USER_AGENT", "")


class SecureLoginView(TokenObtainPairView):
    """
    POST /api/auth/login/

    Custom login view that adds:
    - Rate limiting (LoginRateThrottle)
    - Login failure tracking with temporary lockout
    - Audit logging for both successful and failed logins
    - Generic error messages (user enumeration protection)
    - Security event detection for repeated failures
    """

    throttle_classes = [LoginRateThrottle]

    def post(self, request, *args, **kwargs):
        ip_address = self._get_client_ip(request)
        user_agent = self._get_user_agent(request)
        email = request.data.get("email", "")

        # Check temporary lockout
        if is_login_locked_out(ip_address, email.lower() if email else ""):
            logger.warning(
                "Login attempt while locked out: ip=%s email=%s", ip_address, email
            )
            record_security_event(
                event=SecurityAuditLog.EVENT_LOGIN_LOCKOUT,
                ip_address=ip_address,
                user_agent=user_agent,
                metadata={"email": email, "reason": "lockout_enforced"},
                outcome="failure",
            )
            return Response(
                {
                    "detail": "Too many failed login attempts. "
                    "Please try again later."
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        # Attempt authentication
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except Exception:
            # Record failed login
            should_lockout, fail_count = record_login_failure(
                ip_address, email.lower() if email else ""
            )

            # Try to find the user for audit purposes (without revealing existence)
            target_user = None
            try:
                target_user = User.objects.get(email__iexact=email)
            except (User.DoesNotExist, Exception):
                pass

            record_security_event(
                event=SecurityAuditLog.EVENT_LOGIN_FAILED,
                target_user=target_user,
                ip_address=ip_address,
                user_agent=user_agent,
                metadata={"fail_count": fail_count},
                outcome="failure",
            )

            logger.warning(
                "Login failed: ip=%s email=%s fail_count=%d",
                ip_address, email, fail_count,
            )

            # Route security alert if threshold is approaching
            if should_lockout:
                from core.security import should_emit_security_alert, route_security_alert
                if should_emit_security_alert(
                    "repeated_auth_failures",
                    ip_address=ip_address,
                    target_user=target_user,
                ):
                    route_security_alert(
                        "repeated_auth_failures",
                        metadata={"ip": ip_address, "email": email, "count": fail_count},
                        organization=target_user.role_assignments.first().organization if target_user and target_user.role_assignments.first() else None,
                    )

            # Generic error message — does not reveal whether the email exists
            return Response(
                {"detail": "Invalid email or password."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # Successful login — extract the authenticated user from the serializer
        # simplejwt stores user differently depending on version; look in both locations
        user = serializer.user if hasattr(serializer, "user") else serializer.validated_data.get("user")
        if user is None:
            # Fallback: look up user by email from the validated credentials
            try:
                from accounts.models import User as UserModel
                user = UserModel.objects.get(
                    email__iexact=request.data.get("email", ""),
                    is_active=True,
                )
            except Exception:
                user = None

        if user:
            clear_login_failures(ip_address, user.email.lower())
            record_security_event(
                event=SecurityAuditLog.EVENT_LOGIN,
                actor=user,
                target_user=user,
                ip_address=ip_address,
                user_agent=user_agent,
                organization=self._get_user_org(user),
            )

        return Response(serializer.validated_data, status=status.HTTP_200_OK)

    @staticmethod
    def _get_client_ip(request):
        xff = request.META.get("HTTP_X_FORWARDED_FOR")
        if xff:
            return xff.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR")

    @staticmethod
    def _get_user_agent(request):
        return request.META.get("HTTP_USER_AGENT", "")

    @staticmethod
    def _get_user_org(user):
        """Get the user's primary organization for audit scoping."""
        assignment = user.role_assignments.filter(is_active=True).first()
        return assignment.organization if assignment else None


class PasswordChangeView(APIView):
    """
    POST /api/auth/change-password/

    Requires authentication.  Validates old password, enforces password
    strength rules, revokes existing sessions after change.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = PasswordChangeSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        user = request.user
        old_password = serializer.validated_data["old_password"]
        new_password = serializer.validated_data["new_password"]

        # Verify old password
        if not user.check_password(old_password):
            record_security_event(
                event=SecurityAuditLog.EVENT_PASSWORD_CHANGE,
                actor=user,
                target_user=user,
                ip_address=self._get_client_ip(request),
                user_agent=request.META.get("HTTP_USER_AGENT", ""),
                outcome="failure",
                metadata={"reason": "wrong_old_password"},
            )
            return Response(
                {"detail": "Current password is incorrect."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Set new password
        user.set_password(new_password)
        user.save(update_fields=["password", "updated_at"])

        # Revoke existing sessions
        revoked = revoke_user_sessions(user)

        record_security_event(
            event=SecurityAuditLog.EVENT_PASSWORD_CHANGE,
            actor=user,
            target_user=user,
            ip_address=self._get_client_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
            metadata={"sessions_revoked": revoked},
        )

        return Response(
            {"detail": "Password changed successfully. Please log in again."},
            status=status.HTTP_200_OK,
        )

    @staticmethod
    def _get_client_ip(request):
        xff = request.META.get("HTTP_X_FORWARDED_FOR")
        if xff:
            return xff.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR")


class SecurityAuditLogListView(generics.ListAPIView):
    """
    GET /api/security/audit-log/

    List security audit events.  Restricted to users with the
    ``security.audit.view`` permission.  Results are scoped to the
    user's organization.
    """
    permission_classes = [IsAuthenticated, HasPermission("security.audit.view")]
    serializer_class = SecurityAuditLogSerializer

    def get_queryset(self):
        user = self.request.user
        qs = SecurityAuditLog.objects.select_related(
            "actor", "target_user", "organization"
        ).order_by("-created_at")

        if user.is_superuser or user.is_staff:
            return qs

        # Scope to the user's accessible organizations
        org_ids = set()
        for assignment in user.get_active_assignments():
            if assignment.organization_id:
                org_ids.add(assignment.organization_id)

        # Include events where the user is the actor or target (their own activity)
        from django.db.models import Q
        return qs.filter(
            Q(organization_id__in=org_ids) |
            Q(actor=user) |
            Q(target_user=user)
        ).distinct()


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

        record_security_event(
            event=SecurityAuditLog.EVENT_LOGOUT,
            actor=request.user,
            target_user=request.user,
            ip_address=self._get_client_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
        )

        logger.info("User logged out: %s", request.user.email)
        return Response({"detail": "Successfully logged out."}, status=status.HTTP_200_OK)

    @staticmethod
    def _get_client_ip(request):
        xff = request.META.get("HTTP_X_FORWARDED_FOR")
        if xff:
            return xff.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR")


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
