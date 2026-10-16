# =============================================================================
# RestaurantFlow — Enterprise Views
# Phase 20
#
# URL layout (see enterprise/urls.py):
#
#   GET    /api/enterprise/dashboard/
#
#   GET    /api/enterprise/branches/
#   GET    /api/enterprise/branches/{id}/
#   PATCH  /api/enterprise/branches/{id}/status/
#   POST   /api/enterprise/branches/{id}/open/
#   POST   /api/enterprise/branches/{id}/close/
#   POST   /api/enterprise/branches/{id}/reopen/
#   GET    /api/enterprise/branches/{id}/opening-checklist/
#
#   GET    /api/enterprise/schedules/
#   POST   /api/enterprise/schedules/
#   PUT    /api/enterprise/schedules/bulk/
#   GET    /api/enterprise/schedules/{id}/
#   PUT    /api/enterprise/schedules/{id}/
#
#   GET    /api/enterprise/closures/
#   POST   /api/enterprise/closures/
#   GET    /api/enterprise/closures/{id}/
#   POST   /api/enterprise/closures/{id}/approve/
#   POST   /api/enterprise/closures/{id}/reject/
#   POST   /api/enterprise/closures/{id}/cancel/
#
#   GET    /api/enterprise/configuration/
#   GET    /api/enterprise/configuration/effective/
#   POST   /api/enterprise/configuration/
#   POST   /api/enterprise/configuration/bulk/
#   GET    /api/enterprise/configuration/{id}/
#   PATCH  /api/enterprise/configuration/{id}/
#   POST   /api/enterprise/configuration/{id}/rollback/
#   GET    /api/enterprise/configuration/history/
#
#   GET    /api/enterprise/rollouts/
#   POST   /api/enterprise/rollouts/
#   GET    /api/enterprise/rollouts/{id}/
#   POST   /api/enterprise/rollouts/{id}/preview/
#   POST   /api/enterprise/rollouts/{id}/approve/
#   POST   /api/enterprise/rollouts/{id}/execute/
#   POST   /api/enterprise/rollouts/{id}/cancel/
#
#   GET    /api/enterprise/staff/
#   GET    /api/enterprise/staff/assignments/
#   POST   /api/enterprise/staff/assign/
#   GET    /api/enterprise/staff/transfers/
#   POST   /api/enterprise/staff/transfers/
#   GET    /api/enterprise/staff/transfers/{id}/
#   POST   /api/enterprise/staff/transfers/{id}/approve/
#   POST   /api/enterprise/staff/transfers/{id}/reject/
#   POST   /api/enterprise/staff/transfers/{id}/complete/
#   POST   /api/enterprise/staff/transfers/{id}/cancel/
#
#   GET    /api/enterprise/approval-policies/
#   POST   /api/enterprise/approval-policies/
#   GET    /api/enterprise/approval-policies/{id}/
#   PATCH  /api/enterprise/approval-policies/{id}/
#
#   GET    /api/enterprise/audit/
#
# Security:
#   - All querysets scoped via enterprise.access — IDOR prevention.
#   - get_object() returns 404 (not 403) for unauthorized UUIDs.
#   - Every action checks permission codes, not role names.
#   - Scope (company/restaurant/branch) is NEVER trusted from the payload.
# =============================================================================

import logging

from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts import access as acl
from enterprise import access as ent_acl
from enterprise import (
    branch_services,
    schedule_services,
    rollout_services,
    staff_services,
    services as ent_services,
    selectors,
)
from enterprise.constants import (
    PERM_DASHBOARD_VIEW,
    PERM_BRANCH_VIEW,
    PERM_CONFIG_VIEW,
    PERM_CONFIG_CREATE,
    PERM_CONFIG_UPDATE,
    PERM_CONFIG_HISTORY,
    PERM_ROLLOUT_VIEW,
    PERM_ROLLOUT_CREATE,
    PERM_STAFF_VIEW,
    PERM_STAFF_ASSIGN,
    PERM_STAFF_TRANSFER,
    PERM_STAFF_TRANSFER_APPROVE,
    PERM_SCHEDULE_VIEW,
    PERM_SCHEDULE_MANAGE,
    PERM_APPROVAL_POLICY_VIEW,
    PERM_APPROVAL_POLICY_MANAGE,
    PERM_AUDIT_VIEW,
)
from enterprise.exceptions import (
    BranchStatusTransitionError,
    BranchOperationalBlockError,
    RolloutNotExecutableError,
    StaffTransferBlockedError,
    StaffTransferScopeError,
)
from enterprise.models import (
    BranchOperatingHour,
    BranchClosure,
    EnterpriseConfiguration,
    MenuRollout,
    StaffBranchAssignment,
    StaffTransfer,
    ApprovalPolicy,
)
from enterprise.permissions import (
    HasPermission,
    HasBranchEnterpriseAccess,
    HasRestaurantEnterpriseAccess,
    HasOrganizationEnterpriseAccess,
)
from enterprise.serializers import (
    EnterpriseDashboardSerializer,
    BranchOperationalStatusSerializer,
    SetBranchStatusSerializer,
    BranchOperatingHourSerializer,
    UpsertOperatingHourSerializer,
    BulkUpsertOperatingHoursSerializer,
    BranchClosureSerializer,
    CreateBranchClosureSerializer,
    RejectClosureSerializer,
    EnterpriseConfigurationSerializer,
    SetConfigurationSerializer,
    BulkSetConfigurationSerializer,
    RollbackConfigurationSerializer,
    EffectiveConfigurationSerializer,
    ConfigurationChangeSerializer,
    MenuRolloutSerializer,
    CreateMenuRolloutSerializer,
    RolloutPreviewSerializer,
    StaffBranchAssignmentSerializer,
    AssignStaffSerializer,
    StaffTransferSerializer,
    RequestTransferSerializer,
    RejectTransferSerializer,
    ApprovalPolicySerializer,
    CreateApprovalPolicySerializer,
    UpdateApprovalPolicySerializer,
    EnterpriseAuditLogSerializer,
    ChecklistItemSerializer,
)

logger = logging.getLogger("enterprise")


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _error(code: str, message: str, http_status: int = 400) -> Response:
    return Response(
        {"error": True, "code": code, "message": message},
        status=http_status,
    )


def _service_error(exc) -> Response:
    """Convert service-layer domain exceptions to structured API responses."""
    from rest_framework.exceptions import ValidationError as DRFValidationError
    from rest_framework.exceptions import PermissionDenied as DRFPermDenied

    if isinstance(exc, DRFPermDenied):
        return _error("PERMISSION_DENIED", str(exc), 403)

    if isinstance(exc, DRFValidationError):
        detail = exc.detail
        if isinstance(detail, dict):
            return _error(
                detail.get("code", "VALIDATION_ERROR"),
                detail.get("message", str(exc)),
            )
        return _error("VALIDATION_ERROR", str(exc))

    if hasattr(exc, "code") and hasattr(exc, "message"):
        return _error(exc.code, exc.message)

    return _error("REQUEST_FAILED", str(exc))


def _get_branch_or_404(user, pk):
    """Fetch a Branch scoped to the user's accessible branches. 404 for unauthorized PKs."""
    from organizations.models import Branch
    try:
        branch = acl.get_accessible_branches(user).select_related(
            "restaurant", "restaurant__organization"
        ).get(pk=pk)
        return branch
    except Branch.DoesNotExist:
        raise NotFound(f"Branch {pk} not found.")


def _get_company_from_request(request):
    """Return the first accessible Organization for the authenticated user."""
    orgs = list(acl.get_accessible_organizations(request.user).order_by("name")[:1])
    if not orgs:
        raise PermissionDenied("No accessible organization found.")
    return orgs[0]


def _get_company_for_branch(branch):
    return branch.restaurant.organization


# =============================================================================
# Dashboard
# =============================================================================

class EnterpriseDashboardView(APIView):
    """
    GET /api/enterprise/dashboard/

    Returns aggregated dashboard metrics for the authenticated user's company.
    Permissions: enterprise.dashboard.view
    """

    def get_permissions(self):
        return [IsAuthenticated(), HasPermission(PERM_DASHBOARD_VIEW)()]

    def get(self, request):
        company = _get_company_from_request(request)
        data = selectors.get_enterprise_dashboard(request.user, company)
        return Response(EnterpriseDashboardSerializer(data).data)


# =============================================================================
# Branch list + detail + status actions
# =============================================================================

class BranchListView(generics.ListAPIView):
    """
    GET /api/enterprise/branches/

    Lists all branches accessible to the authenticated user with their
    operational status. Filterable by status, restaurant.
    Permissions: enterprise.branch.view
    """

    serializer_class = BranchOperationalStatusSerializer

    def get_permissions(self):
        return [IsAuthenticated(), HasPermission(PERM_BRANCH_VIEW)()]

    def get_queryset(self):
        qs = ent_acl.get_accessible_branch_statuses(self.request.user).select_related(
            "branch", "branch__restaurant", "status_changed_by"
        )
        status_filter = self.request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)
        restaurant_id = self.request.query_params.get("restaurant_id")
        if restaurant_id:
            qs = qs.filter(branch__restaurant_id=restaurant_id)
        return qs.order_by("branch__restaurant__name", "branch__name")


class BranchDetailView(APIView):
    """
    GET /api/enterprise/branches/{id}/

    Returns aggregated branch detail including status, operating hours, staff.
    Permissions: enterprise.branch.view
    """

    def get_permissions(self):
        return [IsAuthenticated(), HasPermission(PERM_BRANCH_VIEW)()]

    def get(self, request, pk):
        branch = _get_branch_or_404(request.user, pk)
        data = selectors.get_branch_detail(request.user, branch)
        return Response(data)


class BranchSetStatusView(APIView):
    """
    PATCH /api/enterprise/branches/{id}/status/

    Generic status transition (MAINTENANCE, INACTIVE, SCHEDULED_CLOSURE).
    For OPEN/CLOSE/REOPEN use the dedicated endpoints.
    Permissions: enterprise.branch.update
    """

    def get_permissions(self):
        return [IsAuthenticated()]

    def patch(self, request, pk):
        branch = _get_branch_or_404(request.user, pk)
        ser = SetBranchStatusSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            result = branch_services.set_branch_status(
                branch=branch,
                new_status=ser.validated_data["new_status"],
                user=request.user,
                reason=ser.validated_data.get("reason", ""),
            )
            return Response(BranchOperationalStatusSerializer(result).data)
        except Exception as exc:
            return _service_error(exc)


class BranchOpenView(APIView):
    """POST /api/enterprise/branches/{id}/open/"""

    def get_permissions(self):
        return [IsAuthenticated()]

    def post(self, request, pk):
        branch = _get_branch_or_404(request.user, pk)
        reason = request.data.get("reason", "")
        try:
            result = branch_services.open_branch(branch, request.user, reason)
            return Response(BranchOperationalStatusSerializer(result).data)
        except Exception as exc:
            return _service_error(exc)


class BranchCloseView(APIView):
    """POST /api/enterprise/branches/{id}/close/"""

    def get_permissions(self):
        return [IsAuthenticated()]

    def post(self, request, pk):
        branch = _get_branch_or_404(request.user, pk)
        reason = request.data.get("reason", "")
        force  = bool(request.data.get("force", False))
        try:
            result = branch_services.close_branch(branch, request.user, reason, force=force)
            return Response(BranchOperationalStatusSerializer(result).data)
        except BranchOperationalBlockError as exc:
            return _error(exc.code, exc.message, 409)
        except Exception as exc:
            return _service_error(exc)


class BranchReopenView(APIView):
    """POST /api/enterprise/branches/{id}/reopen/"""

    def get_permissions(self):
        return [IsAuthenticated()]

    def post(self, request, pk):
        branch = _get_branch_or_404(request.user, pk)
        reason = request.data.get("reason", "")
        try:
            result = branch_services.reopen_branch(branch, request.user, reason)
            return Response(BranchOperationalStatusSerializer(result).data)
        except Exception as exc:
            return _service_error(exc)


class BranchOpeningChecklistView(APIView):
    """
    GET /api/enterprise/branches/{id}/opening-checklist/

    Returns the operational opening checklist for a branch.
    """

    def get_permissions(self):
        return [IsAuthenticated(), HasPermission(PERM_BRANCH_VIEW)()]

    def get(self, request, pk):
        branch = _get_branch_or_404(request.user, pk)
        try:
            items = branch_services.get_opening_checklist(branch, request.user)
            return Response({"branch_id": str(branch.pk), "checklist": ChecklistItemSerializer(items, many=True).data})
        except Exception as exc:
            return _service_error(exc)


# =============================================================================
# Operating Hours
# =============================================================================

class ScheduleListView(APIView):
    """
    GET /api/enterprise/schedules/?branch_id=...
    POST /api/enterprise/schedules/
    """

    def get_permissions(self):
        return [IsAuthenticated()]

    def get(self, request):
        if not acl.has_permission(request.user, PERM_SCHEDULE_VIEW):
            return _error("PERMISSION_DENIED", "enterprise.schedule.view required.", 403)
        branch_id = request.query_params.get("branch_id")
        if not branch_id:
            return _error("MISSING_PARAM", "branch_id query parameter is required.")
        branch = _get_branch_or_404(request.user, branch_id)
        qs = selectors.get_operating_hours_for_branch(request.user, branch)
        return Response(BranchOperatingHourSerializer(qs, many=True).data)

    def post(self, request):
        if not acl.has_permission(request.user, PERM_SCHEDULE_MANAGE):
            return _error("PERMISSION_DENIED", "enterprise.schedule.manage required.", 403)
        branch_id = request.query_params.get("branch_id") or request.data.get("branch_id")
        if not branch_id:
            return _error("MISSING_PARAM", "branch_id is required.")
        branch = _get_branch_or_404(request.user, branch_id)
        ser = UpsertOperatingHourSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            hour = schedule_services.upsert_operating_hour(
                branch=branch,
                day_of_week=ser.validated_data["day_of_week"],
                opening_time=ser.validated_data.get("opening_time"),
                closing_time=ser.validated_data.get("closing_time"),
                is_closed=ser.validated_data.get("is_closed", False),
                user=request.user,
            )
            return Response(BranchOperatingHourSerializer(hour).data, status=status.HTTP_201_CREATED)
        except Exception as exc:
            return _service_error(exc)


class ScheduleBulkView(APIView):
    """PUT /api/enterprise/schedules/bulk/ — set full week at once."""

    def get_permissions(self):
        return [IsAuthenticated()]

    def put(self, request):
        if not acl.has_permission(request.user, PERM_SCHEDULE_MANAGE):
            return _error("PERMISSION_DENIED", "enterprise.schedule.manage required.", 403)
        branch_id = request.query_params.get("branch_id") or request.data.get("branch_id")
        if not branch_id:
            return _error("MISSING_PARAM", "branch_id is required.")
        branch = _get_branch_or_404(request.user, branch_id)
        ser = BulkUpsertOperatingHoursSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            hours = schedule_services.bulk_upsert_operating_hours(
                branch=branch,
                hours_data=ser.validated_data["hours"],
                user=request.user,
            )
            return Response(BranchOperatingHourSerializer(hours, many=True).data)
        except Exception as exc:
            return _service_error(exc)


# =============================================================================
# Branch Closures
# =============================================================================

class ClosureListCreateView(APIView):
    """
    GET  /api/enterprise/closures/?branch_id=...
    POST /api/enterprise/closures/
    """

    def get_permissions(self):
        return [IsAuthenticated()]

    def get(self, request):
        if not acl.has_permission(request.user, PERM_SCHEDULE_VIEW):
            return _error("PERMISSION_DENIED", "enterprise.schedule.view required.", 403)
        branch_id = request.query_params.get("branch_id")
        if not branch_id:
            return _error("MISSING_PARAM", "branch_id query parameter is required.")
        branch = _get_branch_or_404(request.user, branch_id)
        qs = selectors.get_closures_for_branch(request.user, branch)
        return Response(BranchClosureSerializer(qs, many=True).data)

    def post(self, request):
        if not acl.has_permission(request.user, PERM_SCHEDULE_MANAGE):
            return _error("PERMISSION_DENIED", "enterprise.schedule.manage required.", 403)
        branch_id = request.data.get("branch_id")
        if not branch_id:
            return _error("MISSING_PARAM", "branch_id is required.")
        branch = _get_branch_or_404(request.user, branch_id)
        ser = CreateBranchClosureSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            closure = schedule_services.create_branch_closure(
                branch=branch,
                closure_type=ser.validated_data["closure_type"],
                start_datetime=ser.validated_data["start_datetime"],
                end_datetime=ser.validated_data["end_datetime"],
                reason=ser.validated_data["reason"],
                user=request.user,
                auto_approve=ser.validated_data.get("auto_approve", False),
            )
            return Response(BranchClosureSerializer(closure).data, status=status.HTTP_201_CREATED)
        except Exception as exc:
            return _service_error(exc)


def _get_closure_or_404(user, pk):
    try:
        return ent_acl.get_accessible_closures(user).select_related(
            "branch", "branch__restaurant", "created_by", "approved_by"
        ).get(pk=pk)
    except BranchClosure.DoesNotExist:
        raise NotFound(f"Closure {pk} not found.")


class ClosureDetailView(APIView):
    """GET /api/enterprise/closures/{id}/"""

    def get_permissions(self):
        return [IsAuthenticated(), HasPermission(PERM_SCHEDULE_VIEW)()]

    def get(self, request, pk):
        closure = _get_closure_or_404(request.user, pk)
        return Response(BranchClosureSerializer(closure).data)


class ClosureApproveView(APIView):
    """POST /api/enterprise/closures/{id}/approve/"""

    def get_permissions(self):
        return [IsAuthenticated(), HasPermission(PERM_SCHEDULE_MANAGE)()]

    def post(self, request, pk):
        closure = _get_closure_or_404(request.user, pk)
        try:
            result = schedule_services.approve_branch_closure(closure, request.user)
            return Response(BranchClosureSerializer(result).data)
        except Exception as exc:
            return _service_error(exc)


class ClosureRejectView(APIView):
    """POST /api/enterprise/closures/{id}/reject/"""

    def get_permissions(self):
        return [IsAuthenticated(), HasPermission(PERM_SCHEDULE_MANAGE)()]

    def post(self, request, pk):
        closure = _get_closure_or_404(request.user, pk)
        ser = RejectClosureSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            result = schedule_services.reject_branch_closure(
                closure, request.user, ser.validated_data.get("rejection_reason", "")
            )
            return Response(BranchClosureSerializer(result).data)
        except Exception as exc:
            return _service_error(exc)


class ClosureCancelView(APIView):
    """POST /api/enterprise/closures/{id}/cancel/"""

    def get_permissions(self):
        return [IsAuthenticated(), HasPermission(PERM_SCHEDULE_MANAGE)()]

    def post(self, request, pk):
        closure = _get_closure_or_404(request.user, pk)
        try:
            result = schedule_services.cancel_branch_closure(closure, request.user)
            return Response(BranchClosureSerializer(result).data)
        except Exception as exc:
            return _service_error(exc)


# =============================================================================
# Enterprise Configuration
# =============================================================================

def _resolve_config_scope_from_request(request):
    """Extract and validate scope objects from query params / payload."""
    data = request.data if request.method != "GET" else request.query_params
    branch_id     = data.get("branch_id")
    restaurant_id = data.get("restaurant_id")
    company_id    = data.get("company_id")

    branch     = None
    restaurant = None
    company    = None

    if branch_id:
        branch = _get_branch_or_404(request.user, branch_id)
        restaurant = branch.restaurant
        company    = restaurant.organization
    elif restaurant_id:
        accessible = acl.get_accessible_restaurants(request.user)
        try:
            restaurant = accessible.select_related("organization").get(pk=restaurant_id)
            company    = restaurant.organization
        except Exception:
            raise NotFound(f"Restaurant {restaurant_id} not found.")
    elif company_id:
        accessible = acl.get_accessible_organizations(request.user)
        try:
            company = accessible.get(pk=company_id)
        except Exception:
            raise NotFound(f"Company {company_id} not found.")
    else:
        company = _get_company_from_request(request)

    return company, restaurant, branch


class ConfigurationListCreateView(APIView):
    """
    GET  /api/enterprise/configuration/
    POST /api/enterprise/configuration/
    """

    def get_permissions(self):
        return [IsAuthenticated()]

    def get(self, request):
        if not acl.has_permission(request.user, PERM_CONFIG_VIEW):
            return _error("PERMISSION_DENIED", "enterprise.configuration.view required.", 403)
        company, restaurant, branch = _resolve_config_scope_from_request(request)
        qs = selectors.get_configurations_for_scope(
            request.user, company, restaurant, branch
        )
        return Response(EnterpriseConfigurationSerializer(qs, many=True).data)

    def post(self, request):
        if not acl.has_permission(request.user, PERM_CONFIG_CREATE):
            return _error("PERMISSION_DENIED", "enterprise.configuration.create required.", 403)
        company, restaurant, branch = _resolve_config_scope_from_request(request)
        ser = SetConfigurationSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            config = ent_services.set_configuration(
                company=company,
                key=ser.validated_data["configuration_key"],
                value=ser.validated_data["configuration_value"],
                user=request.user,
                restaurant=restaurant,
                branch=branch,
                reason=ser.validated_data.get("reason", ""),
            )
            return Response(
                EnterpriseConfigurationSerializer(config).data,
                status=status.HTTP_201_CREATED,
            )
        except Exception as exc:
            return _service_error(exc)


class ConfigurationBulkView(APIView):
    """POST /api/enterprise/configuration/bulk/"""

    def get_permissions(self):
        return [IsAuthenticated(), HasPermission(PERM_CONFIG_UPDATE)()]

    def post(self, request):
        company, restaurant, branch = _resolve_config_scope_from_request(request)
        ser = BulkSetConfigurationSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        result = ent_services.bulk_set_configurations(
            company=company,
            configs=ser.validated_data["configs"],
            user=request.user,
            restaurant=restaurant,
            branch=branch,
            reason=ser.validated_data.get("reason", ""),
        )
        http_status = (
            status.HTTP_200_OK
            if not result["failed"]
            else status.HTTP_207_MULTI_STATUS
        )
        return Response(result, status=http_status)


class ConfigurationEffectiveView(APIView):
    """
    GET /api/enterprise/configuration/effective/?branch_id=...

    Returns the fully resolved effective configuration for a scope,
    showing value + source per key.
    """

    def get_permissions(self):
        return [IsAuthenticated(), HasPermission(PERM_CONFIG_VIEW)()]

    def get(self, request):
        company, restaurant, branch = _resolve_config_scope_from_request(request)
        if branch:
            effective = selectors.get_effective_configuration_for_branch(request.user, branch)
        else:
            from enterprise.configuration_resolver import ConfigurationResolver
            if restaurant:
                effective = ConfigurationResolver.get_restaurant_configuration(restaurant)
            else:
                effective = ConfigurationResolver.get_company_configuration(company)

        result = [{"key": k, **v} for k, v in effective.items()]
        return Response(EffectiveConfigurationSerializer(result, many=True).data)


def _get_config_or_404(user, pk):
    try:
        return ent_acl.get_accessible_configurations(user).select_related(
            "company", "restaurant", "branch", "created_by", "updated_by"
        ).get(pk=pk)
    except EnterpriseConfiguration.DoesNotExist:
        raise NotFound(f"Configuration {pk} not found.")


class ConfigurationDetailView(APIView):
    """
    GET   /api/enterprise/configuration/{id}/
    PATCH /api/enterprise/configuration/{id}/
    """

    def get_permissions(self):
        return [IsAuthenticated()]

    def get(self, request, pk):
        if not acl.has_permission(request.user, PERM_CONFIG_VIEW):
            return _error("PERMISSION_DENIED", "enterprise.configuration.view required.", 403)
        config = _get_config_or_404(request.user, pk)
        return Response(EnterpriseConfigurationSerializer(config).data)

    def patch(self, request, pk):
        if not acl.has_permission(request.user, PERM_CONFIG_UPDATE):
            return _error("PERMISSION_DENIED", "enterprise.configuration.update required.", 403)
        config = _get_config_or_404(request.user, pk)
        ser = SetConfigurationSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            updated = ent_services.set_configuration(
                company=config.company,
                key=ser.validated_data.get("configuration_key", config.configuration_key),
                value=ser.validated_data["configuration_value"],
                user=request.user,
                restaurant=config.restaurant,
                branch=config.branch,
                reason=ser.validated_data.get("reason", ""),
            )
            return Response(EnterpriseConfigurationSerializer(updated).data)
        except Exception as exc:
            return _service_error(exc)


class ConfigurationRollbackView(APIView):
    """POST /api/enterprise/configuration/{id}/rollback/"""

    def get_permissions(self):
        return [IsAuthenticated(), HasPermission(PERM_CONFIG_UPDATE)()]

    def post(self, request, pk):
        config = _get_config_or_404(request.user, pk)
        ser = RollbackConfigurationSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            restored = ent_services.rollback_configuration(
                config=config,
                user=request.user,
                reason=ser.validated_data.get("reason", ""),
            )
            return Response(EnterpriseConfigurationSerializer(restored).data)
        except Exception as exc:
            return _service_error(exc)


class ConfigurationHistoryView(APIView):
    """GET /api/enterprise/configuration/history/"""

    def get_permissions(self):
        return [IsAuthenticated(), HasPermission(PERM_CONFIG_HISTORY)()]

    def get(self, request):
        company = _get_company_from_request(request)
        key = request.query_params.get("key")
        qs = selectors.get_configuration_history(request.user, company, key)
        return Response(ConfigurationChangeSerializer(qs, many=True).data)


# =============================================================================
# Rollouts
# =============================================================================

def _get_restaurant_for_request(request):
    """Resolve a Restaurant from query param or payload restaurant_id."""
    restaurant_id = (
        request.query_params.get("restaurant_id")
        or request.data.get("restaurant_id")
    )
    if not restaurant_id:
        raise NotFound("restaurant_id is required.")
    accessible = acl.get_accessible_restaurants(request.user)
    try:
        return accessible.select_related("organization").get(pk=restaurant_id)
    except Exception:
        raise NotFound(f"Restaurant {restaurant_id} not found.")


def _get_rollout_or_404(user, pk):
    try:
        return ent_acl.get_accessible_rollouts(user).select_related(
            "restaurant", "menu_item", "created_by", "approved_by", "source_branch"
        ).prefetch_related("branch_results__branch", "target_branches").get(pk=pk)
    except MenuRollout.DoesNotExist:
        raise NotFound(f"Rollout {pk} not found.")


class RolloutListCreateView(APIView):
    """
    GET  /api/enterprise/rollouts/?restaurant_id=...
    POST /api/enterprise/rollouts/
    """

    def get_permissions(self):
        return [IsAuthenticated()]

    def get(self, request):
        if not acl.has_permission(request.user, PERM_ROLLOUT_VIEW):
            return _error("PERMISSION_DENIED", "enterprise.rollout.view required.", 403)
        restaurant = _get_restaurant_for_request(request)
        qs = selectors.get_rollouts_for_restaurant(request.user, restaurant)
        return Response(MenuRolloutSerializer(qs, many=True).data)

    def post(self, request):
        if not acl.has_permission(request.user, PERM_ROLLOUT_CREATE):
            return _error("PERMISSION_DENIED", "enterprise.rollout.create required.", 403)
        restaurant = _get_restaurant_for_request(request)
        ser = CreateMenuRolloutSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        # Resolve menu_item
        from menu.models import MenuItem
        try:
            menu_item = MenuItem.objects.get(
                pk=ser.validated_data["menu_item_id"],
                restaurant=restaurant,
            )
        except MenuItem.DoesNotExist:
            return _error("MENU_ITEM_NOT_FOUND", "Menu item not found in this restaurant.")

        try:
            from enterprise.constants import ROLLOUT_TYPE_PRICE, ROLLOUT_TYPE_MENU_AVAILABILITY
            rtype = ser.validated_data["rollout_type"]
            if rtype == ROLLOUT_TYPE_PRICE:
                rollout = rollout_services.create_price_rollout(
                    restaurant=restaurant,
                    menu_item=menu_item,
                    new_price=ser.validated_data["new_price"],
                    target_scope=ser.validated_data["target_scope"],
                    user=request.user,
                    target_branch_ids=[str(b) for b in ser.validated_data.get("target_branch_ids", [])],
                    force_override=ser.validated_data.get("force_override", False),
                    effective_from=ser.validated_data.get("effective_from"),
                    notes=ser.validated_data.get("notes", ""),
                )
            else:
                rollout = rollout_services.create_menu_rollout(
                    restaurant=restaurant,
                    menu_item=menu_item,
                    target_scope=ser.validated_data["target_scope"],
                    is_available=ser.validated_data["is_available"],
                    user=request.user,
                    target_branch_ids=[str(b) for b in ser.validated_data.get("target_branch_ids", [])],
                    force_override=ser.validated_data.get("force_override", False),
                    notes=ser.validated_data.get("notes", ""),
                )
            return Response(MenuRolloutSerializer(rollout).data, status=status.HTTP_201_CREATED)
        except Exception as exc:
            return _service_error(exc)


class RolloutDetailView(APIView):
    """GET /api/enterprise/rollouts/{id}/"""

    def get_permissions(self):
        return [IsAuthenticated(), HasPermission(PERM_ROLLOUT_VIEW)()]

    def get(self, request, pk):
        rollout = _get_rollout_or_404(request.user, pk)
        return Response(MenuRolloutSerializer(rollout).data)


class RolloutPreviewView(APIView):
    """POST /api/enterprise/rollouts/{id}/preview/"""

    def get_permissions(self):
        return [IsAuthenticated()]

    def post(self, request, pk):
        from enterprise.constants import PERM_ROLLOUT_PREVIEW
        if not acl.has_permission(request.user, PERM_ROLLOUT_PREVIEW):
            return _error("PERMISSION_DENIED", "enterprise.rollout.preview required.", 403)
        rollout = _get_rollout_or_404(request.user, pk)
        try:
            preview = rollout_services.preview_rollout(rollout, request.user)
            return Response(RolloutPreviewSerializer(preview).data)
        except Exception as exc:
            return _service_error(exc)


class RolloutApproveView(APIView):
    """POST /api/enterprise/rollouts/{id}/approve/"""

    def get_permissions(self):
        return [IsAuthenticated()]

    def post(self, request, pk):
        from enterprise.constants import PERM_ROLLOUT_APPROVE
        if not acl.has_permission(request.user, PERM_ROLLOUT_APPROVE):
            return _error("PERMISSION_DENIED", "enterprise.rollout.approve required.", 403)
        rollout = _get_rollout_or_404(request.user, pk)
        try:
            result = rollout_services.approve_rollout(rollout, request.user)
            return Response(MenuRolloutSerializer(result).data)
        except Exception as exc:
            return _service_error(exc)


class RolloutExecuteView(APIView):
    """POST /api/enterprise/rollouts/{id}/execute/"""

    def get_permissions(self):
        return [IsAuthenticated()]

    def post(self, request, pk):
        from enterprise.constants import PERM_ROLLOUT_EXECUTE
        if not acl.has_permission(request.user, PERM_ROLLOUT_EXECUTE):
            return _error("PERMISSION_DENIED", "enterprise.rollout.execute required.", 403)
        rollout = _get_rollout_or_404(request.user, pk)
        try:
            result = rollout_services.execute_rollout(rollout, request.user)
            http_status = (
                status.HTTP_200_OK
                if not result["failed"]
                else status.HTTP_207_MULTI_STATUS
            )
            return Response(result, status=http_status)
        except RolloutNotExecutableError as exc:
            return _error(exc.code, exc.message, 409)
        except Exception as exc:
            return _service_error(exc)


class RolloutCancelView(APIView):
    """POST /api/enterprise/rollouts/{id}/cancel/"""

    def get_permissions(self):
        return [IsAuthenticated()]

    def post(self, request, pk):
        from enterprise.constants import PERM_ROLLOUT_CANCEL
        if not acl.has_permission(request.user, PERM_ROLLOUT_CANCEL):
            return _error("PERMISSION_DENIED", "enterprise.rollout.cancel required.", 403)
        rollout = _get_rollout_or_404(request.user, pk)
        reason = request.data.get("reason", "")
        try:
            result = rollout_services.cancel_rollout(rollout, request.user, reason)
            return Response(MenuRolloutSerializer(result).data)
        except Exception as exc:
            return _service_error(exc)


# =============================================================================
# Staff
# =============================================================================

def _get_assignment_or_404(user, pk):
    try:
        return ent_acl.get_accessible_assignments(user).select_related(
            "user", "branch", "restaurant", "role", "assigned_by"
        ).get(pk=pk)
    except StaffBranchAssignment.DoesNotExist:
        raise NotFound(f"Staff assignment {pk} not found.")


def _get_transfer_or_404(user, pk):
    try:
        return ent_acl.get_accessible_transfers(user).select_related(
            "user", "restaurant", "source_branch", "destination_branch",
            "requested_by", "approved_by"
        ).get(pk=pk)
    except StaffTransfer.DoesNotExist:
        raise NotFound(f"Staff transfer {pk} not found.")


class StaffOverviewView(APIView):
    """GET /api/enterprise/staff/?restaurant_id=..."""

    def get_permissions(self):
        return [IsAuthenticated(), HasPermission(PERM_STAFF_VIEW)()]

    def get(self, request):
        restaurant = _get_restaurant_for_request(request)
        qs = selectors.get_staff_overview_for_restaurant(request.user, restaurant)
        return Response(StaffBranchAssignmentSerializer(qs, many=True).data)


class StaffAssignmentListView(APIView):
    """GET /api/enterprise/staff/assignments/?branch_id=..."""

    def get_permissions(self):
        return [IsAuthenticated(), HasPermission(PERM_STAFF_VIEW)()]

    def get(self, request):
        branch_id = request.query_params.get("branch_id")
        if not branch_id:
            return _error("MISSING_PARAM", "branch_id query parameter is required.")
        branch = _get_branch_or_404(request.user, branch_id)
        qs = selectors.get_assignments_for_branch(request.user, branch)
        return Response(StaffBranchAssignmentSerializer(qs, many=True).data)


class StaffAssignView(APIView):
    """POST /api/enterprise/staff/assign/"""

    def get_permissions(self):
        return [IsAuthenticated(), HasPermission(PERM_STAFF_ASSIGN)()]

    def post(self, request):
        branch_id = request.data.get("branch_id")
        if not branch_id:
            return _error("MISSING_PARAM", "branch_id is required.")
        branch = _get_branch_or_404(request.user, branch_id)
        ser = AssignStaffSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        # Resolve user
        from django.contrib.auth import get_user_model
        User = get_user_model()
        try:
            user_to_assign = User.objects.get(pk=ser.validated_data["user_id"])
        except User.DoesNotExist:
            return _error("USER_NOT_FOUND", "User not found.")

        # Resolve role
        from accounts.models import Role
        try:
            role = Role.objects.get(pk=ser.validated_data["role_id"])
        except Role.DoesNotExist:
            return _error("ROLE_NOT_FOUND", "Role not found.")

        try:
            assignment = staff_services.assign_staff_to_branch(
                user_to_assign=user_to_assign,
                branch=branch,
                role=role,
                assigned_by=request.user,
                start_date=ser.validated_data.get("start_date"),
                end_date=ser.validated_data.get("end_date"),
                is_primary=ser.validated_data.get("is_primary", True),
            )
            return Response(
                StaffBranchAssignmentSerializer(assignment).data,
                status=status.HTTP_201_CREATED,
            )
        except Exception as exc:
            return _service_error(exc)


class StaffTransferListCreateView(APIView):
    """
    GET  /api/enterprise/staff/transfers/?restaurant_id=...
    POST /api/enterprise/staff/transfers/
    """

    def get_permissions(self):
        return [IsAuthenticated()]

    def get(self, request):
        if not acl.has_permission(request.user, PERM_STAFF_VIEW):
            return _error("PERMISSION_DENIED", "enterprise.staff.view required.", 403)
        restaurant = _get_restaurant_for_request(request)
        qs = selectors.get_transfers_for_restaurant(request.user, restaurant)
        return Response(StaffTransferSerializer(qs, many=True).data)

    def post(self, request):
        if not acl.has_permission(request.user, PERM_STAFF_TRANSFER):
            return _error("PERMISSION_DENIED", "enterprise.staff.transfer required.", 403)
        ser = RequestTransferSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        # Resolve source branch from request
        source_branch_id = request.data.get("source_branch_id")
        if not source_branch_id:
            return _error("MISSING_PARAM", "source_branch_id is required.")
        source_branch = _get_branch_or_404(request.user, source_branch_id)

        # Resolve destination branch
        dest_branch = _get_branch_or_404(
            request.user, ser.validated_data["destination_branch_id"]
        )

        # Resolve user to transfer
        from django.contrib.auth import get_user_model
        User = get_user_model()
        try:
            user_to_transfer = User.objects.get(pk=ser.validated_data["user_id"])
        except User.DoesNotExist:
            return _error("USER_NOT_FOUND", "User not found.")

        try:
            transfer = staff_services.request_staff_transfer(
                user_to_transfer=user_to_transfer,
                source_branch=source_branch,
                destination_branch=dest_branch,
                requested_by=request.user,
                reason=ser.validated_data["reason"],
            )
            return Response(
                StaffTransferSerializer(transfer).data,
                status=status.HTTP_201_CREATED,
            )
        except (StaffTransferBlockedError, StaffTransferScopeError) as exc:
            return _error(exc.code, exc.message, 409)
        except Exception as exc:
            return _service_error(exc)


class StaffTransferDetailView(APIView):
    """GET /api/enterprise/staff/transfers/{id}/"""

    def get_permissions(self):
        return [IsAuthenticated(), HasPermission(PERM_STAFF_VIEW)()]

    def get(self, request, pk):
        transfer = _get_transfer_or_404(request.user, pk)
        return Response(StaffTransferSerializer(transfer).data)


class StaffTransferApproveView(APIView):
    """POST /api/enterprise/staff/transfers/{id}/approve/"""

    def get_permissions(self):
        return [IsAuthenticated(), HasPermission(PERM_STAFF_TRANSFER_APPROVE)()]

    def post(self, request, pk):
        transfer = _get_transfer_or_404(request.user, pk)
        try:
            result = staff_services.approve_staff_transfer(transfer, request.user)
            return Response(StaffTransferSerializer(result).data)
        except Exception as exc:
            return _service_error(exc)


class StaffTransferRejectView(APIView):
    """POST /api/enterprise/staff/transfers/{id}/reject/"""

    def get_permissions(self):
        return [IsAuthenticated(), HasPermission(PERM_STAFF_TRANSFER_APPROVE)()]

    def post(self, request, pk):
        transfer = _get_transfer_or_404(request.user, pk)
        ser = RejectTransferSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            result = staff_services.reject_staff_transfer(
                transfer, request.user, ser.validated_data.get("rejection_reason", "")
            )
            return Response(StaffTransferSerializer(result).data)
        except Exception as exc:
            return _service_error(exc)


class StaffTransferCompleteView(APIView):
    """POST /api/enterprise/staff/transfers/{id}/complete/"""

    def get_permissions(self):
        return [IsAuthenticated(), HasPermission(PERM_STAFF_TRANSFER_APPROVE)()]

    def post(self, request, pk):
        transfer = _get_transfer_or_404(request.user, pk)
        try:
            result = staff_services.complete_staff_transfer(transfer, request.user)
            return Response(StaffTransferSerializer(result).data)
        except (StaffTransferBlockedError, StaffTransferScopeError) as exc:
            return _error(exc.code, exc.message, 409)
        except Exception as exc:
            return _service_error(exc)


class StaffTransferCancelView(APIView):
    """POST /api/enterprise/staff/transfers/{id}/cancel/"""

    def get_permissions(self):
        return [IsAuthenticated()]

    def post(self, request, pk):
        transfer = _get_transfer_or_404(request.user, pk)
        try:
            result = staff_services.cancel_staff_transfer(transfer, request.user)
            return Response(StaffTransferSerializer(result).data)
        except Exception as exc:
            return _service_error(exc)


# =============================================================================
# Approval Policies
# =============================================================================

def _get_policy_or_404(user, pk):
    try:
        return ent_acl.get_accessible_approval_policies(user).select_related(
            "company", "restaurant", "branch", "required_role", "created_by", "updated_by"
        ).get(pk=pk)
    except ApprovalPolicy.DoesNotExist:
        raise NotFound(f"Approval policy {pk} not found.")


class ApprovalPolicyListCreateView(APIView):
    """
    GET  /api/enterprise/approval-policies/
    POST /api/enterprise/approval-policies/
    """

    def get_permissions(self):
        return [IsAuthenticated()]

    def get(self, request):
        if not acl.has_permission(request.user, PERM_APPROVAL_POLICY_VIEW):
            return _error("PERMISSION_DENIED", "enterprise.approval_policy.view required.", 403)
        company = _get_company_from_request(request)
        policy_type = request.query_params.get("policy_type")
        qs = selectors.get_approval_policies_for_company(
            request.user, company, policy_type=policy_type
        )
        return Response(ApprovalPolicySerializer(qs, many=True).data)

    def post(self, request):
        if not acl.has_permission(request.user, PERM_APPROVAL_POLICY_MANAGE):
            return _error("PERMISSION_DENIED", "enterprise.approval_policy.manage required.", 403)
        company, restaurant, branch = _resolve_config_scope_from_request(request)
        ser = CreateApprovalPolicySerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        required_role = None
        if ser.validated_data.get("required_role_id"):
            from accounts.models import Role
            try:
                required_role = Role.objects.get(pk=ser.validated_data["required_role_id"])
            except Role.DoesNotExist:
                return _error("ROLE_NOT_FOUND", "Required role not found.")

        try:
            policy = ent_services.create_approval_policy(
                company=company,
                policy_type=ser.validated_data["policy_type"],
                required_permission=ser.validated_data["required_permission"],
                user=request.user,
                restaurant=restaurant,
                branch=branch,
                threshold_amount=ser.validated_data.get("threshold_amount"),
                threshold_percentage=ser.validated_data.get("threshold_percentage"),
                required_role=required_role,
            )
            return Response(ApprovalPolicySerializer(policy).data, status=status.HTTP_201_CREATED)
        except Exception as exc:
            return _service_error(exc)


class ApprovalPolicyDetailView(APIView):
    """
    GET   /api/enterprise/approval-policies/{id}/
    PATCH /api/enterprise/approval-policies/{id}/
    """

    def get_permissions(self):
        return [IsAuthenticated()]

    def get(self, request, pk):
        if not acl.has_permission(request.user, PERM_APPROVAL_POLICY_VIEW):
            return _error("PERMISSION_DENIED", "enterprise.approval_policy.view required.", 403)
        policy = _get_policy_or_404(request.user, pk)
        return Response(ApprovalPolicySerializer(policy).data)

    def patch(self, request, pk):
        if not acl.has_permission(request.user, PERM_APPROVAL_POLICY_MANAGE):
            return _error("PERMISSION_DENIED", "enterprise.approval_policy.manage required.", 403)
        policy = _get_policy_or_404(request.user, pk)
        ser = UpdateApprovalPolicySerializer(data=request.data, partial=True)
        ser.is_valid(raise_exception=True)

        kwargs = dict(ser.validated_data)
        if "required_role_id" in kwargs:
            rid = kwargs.pop("required_role_id")
            if rid:
                from accounts.models import Role
                try:
                    kwargs["required_role"] = Role.objects.get(pk=rid)
                except Role.DoesNotExist:
                    return _error("ROLE_NOT_FOUND", "Required role not found.")
            else:
                kwargs["required_role"] = None

        try:
            updated = ent_services.update_approval_policy(policy, request.user, **kwargs)
            return Response(ApprovalPolicySerializer(updated).data)
        except Exception as exc:
            return _service_error(exc)


# =============================================================================
# Audit Log
# =============================================================================

class AuditLogListView(APIView):
    """GET /api/enterprise/audit/"""

    def get_permissions(self):
        return [IsAuthenticated(), HasPermission(PERM_AUDIT_VIEW)()]

    def get(self, request):
        company = _get_company_from_request(request)
        restaurant_id = request.query_params.get("restaurant_id")
        branch_id     = request.query_params.get("branch_id")
        action        = request.query_params.get("action")

        restaurant = None
        branch     = None

        if branch_id:
            branch = _get_branch_or_404(request.user, branch_id)
            restaurant = branch.restaurant
        elif restaurant_id:
            accessible = acl.get_accessible_restaurants(request.user)
            try:
                restaurant = accessible.get(pk=restaurant_id)
            except Exception:
                raise NotFound(f"Restaurant {restaurant_id} not found.")

        qs = selectors.get_audit_logs(
            request.user, company,
            restaurant=restaurant,
            branch=branch,
            action=action,
        )
        return Response(EnterpriseAuditLogSerializer(qs, many=True).data)
