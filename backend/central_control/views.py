# =============================================================================
# RestaurantFlow — Central Control Center Views
# Phase 15
#
# Views are thin: they validate input, call services/selectors, return responses.
# Business logic stays in services/selectors.
#
# Endpoints:
#   GET  /api/central-control/dashboard/
#   GET  /api/central-control/restaurants/
#   GET  /api/central-control/restaurants/health/
#   GET  /api/central-control/branches/
#   GET  /api/central-control/alerts/
#   POST /api/central-control/alerts/
#   GET  /api/central-control/alerts/<pk>/
#   POST /api/central-control/alerts/<pk>/acknowledge/
#   POST /api/central-control/alerts/<pk>/resolve/
#   POST /api/central-control/alerts/<pk>/dismiss/
#   GET  /api/central-control/issues/
#   POST /api/central-control/issues/
#   GET  /api/central-control/issues/<pk>/
#   POST /api/central-control/issues/<pk>/assign/
#   POST /api/central-control/issues/<pk>/start/
#   POST /api/central-control/issues/<pk>/resolve/
#   POST /api/central-control/issues/<pk>/close/
#   POST /api/central-control/issues/<pk>/cancel/
#   PATCH/api/central-control/issues/<pk>/
#   GET  /api/central-control/events/
#   GET  /api/central-control/system-health/
#   GET  /api/central-control/settings/
#   PATCH/api/central-control/settings/
#   GET  /api/central-control/audit/
#   GET  /api/central-control/users/
#   POST /api/central-control/run-detection/   (admin/management endpoint)
# =============================================================================

import logging

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.pagination import PageNumberPagination

from central_control.constants import (
    PERM_DASHBOARD_VIEW, PERM_RESTAURANT_VIEW, PERM_BRANCH_VIEW,
    PERM_ALERT_VIEW, PERM_ALERT_ACKNOWLEDGE, PERM_ALERT_RESOLVE, PERM_ALERT_DISMISS,
    PERM_ISSUE_VIEW, PERM_ISSUE_CREATE, PERM_ISSUE_ASSIGN, PERM_ISSUE_UPDATE,
    PERM_ISSUE_RESOLVE, PERM_ISSUE_CLOSE,
    PERM_HEALTH_VIEW, PERM_SYSTEM_EVENT_VIEW, PERM_AUDIT_VIEW,
    PERM_USER_ACCESS_VIEW, PERM_CONFIGURATION_VIEW, PERM_CONFIGURATION_MANAGE,
)
from central_control.permissions import HasCentralPermission, IsCentralControlUser
from central_control.exceptions import (
    AlertNotFoundError, AlertTransitionError,
    IssueNotFoundError, IssueTransitionError, IssueImmutableError,
    IssueAssignmentScopeError, ResolutionNoteRequiredError,
    ScopeViolationError,
)

logger = logging.getLogger("central_control")


class CentralControlPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 200


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

class CentralDashboardView(APIView):
    """
    GET /api/central-control/dashboard/

    Returns organization-level KPIs for the Central Control Center.
    Requires: central_control.dashboard.view
    """
    permission_classes = [IsAuthenticated, HasCentralPermission(PERM_DASHBOARD_VIEW)]

    def get(self, request):
        from central_control.dashboard_services import get_central_dashboard

        organization_id = request.query_params.get("organization_id")
        try:
            data = get_central_dashboard(request.user, organization_id=organization_id)
            return Response(data)
        except ScopeViolationError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN)
        except Exception as exc:
            logger.error("CentralDashboardView error: %s", exc, exc_info=True)
            return Response(
                {"detail": "Dashboard unavailable."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )


# ---------------------------------------------------------------------------
# Restaurant overview
# ---------------------------------------------------------------------------

class RestaurantOverviewView(APIView):
    """
    GET /api/central-control/restaurants/

    Returns scoped restaurant list with health and alert summaries.
    Requires: central_control.restaurant.view
    """
    permission_classes = [IsAuthenticated, HasCentralPermission(PERM_RESTAURANT_VIEW)]

    def get(self, request):
        from central_control.selectors import get_restaurants_for_user
        from central_control.serializers import RestaurantOverviewSerializer

        organization_id = request.query_params.get("organization_id")
        is_active_param = request.query_params.get("is_active")
        is_active = None
        if is_active_param is not None:
            is_active = is_active_param.lower() in ("true", "1")

        qs = get_restaurants_for_user(
            request.user,
            organization_id=organization_id,
            is_active=is_active,
        )
        paginator = CentralControlPagination()
        page = paginator.paginate_queryset(qs, request)
        serializer = RestaurantOverviewSerializer(page, many=True, context={"request": request})
        return paginator.get_paginated_response(serializer.data)


class RestaurantHealthView(APIView):
    """
    GET /api/central-control/restaurants/health/

    Returns health status for each accessible restaurant.
    Requires: central_control.health.view
    """
    permission_classes = [IsAuthenticated, HasCentralPermission(PERM_HEALTH_VIEW)]

    def get(self, request):
        from central_control.dashboard_services import get_restaurant_health_list

        organization_id = request.query_params.get("organization_id")
        try:
            data = get_restaurant_health_list(request.user, organization_id=organization_id)
            return Response({"results": data, "count": len(data)})
        except ScopeViolationError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN)


# ---------------------------------------------------------------------------
# Branch overview
# ---------------------------------------------------------------------------

class BranchOverviewView(APIView):
    """
    GET /api/central-control/branches/

    Returns scoped branch list with operational summaries.
    Requires: central_control.branch.view
    """
    permission_classes = [IsAuthenticated, HasCentralPermission(PERM_BRANCH_VIEW)]

    def get(self, request):
        from central_control.selectors import get_branches_for_user
        from central_control.serializers import BranchOverviewSerializer

        organization_id = request.query_params.get("organization_id")
        restaurant_id = request.query_params.get("restaurant_id")
        is_active_param = request.query_params.get("is_active")
        is_active = None
        if is_active_param is not None:
            is_active = is_active_param.lower() in ("true", "1")

        qs = get_branches_for_user(
            request.user,
            organization_id=organization_id,
            restaurant_id=restaurant_id,
            is_active=is_active,
        )
        paginator = CentralControlPagination()
        page = paginator.paginate_queryset(qs, request)
        serializer = BranchOverviewSerializer(page, many=True, context={"request": request})
        return paginator.get_paginated_response(serializer.data)


# ---------------------------------------------------------------------------
# Alerts
# ---------------------------------------------------------------------------

class AlertListView(APIView):
    """
    GET  /api/central-control/alerts/   — list with filtering
    Requires: central_control.alert.view
    """
    permission_classes = [IsAuthenticated, HasCentralPermission(PERM_ALERT_VIEW)]

    def get(self, request):
        from central_control.selectors import get_alerts_for_user
        from central_control.serializers import CentralAlertSerializer

        qs = get_alerts_for_user(
            request.user,
            organization_id=request.query_params.get("organization_id"),
            restaurant_id=request.query_params.get("restaurant_id"),
            branch_id=request.query_params.get("branch_id"),
            severity=request.query_params.get("severity"),
            status=request.query_params.get("status"),
            alert_type=request.query_params.get("alert_type"),
            search=request.query_params.get("search"),
            ordering=request.query_params.get("ordering", "-detected_at"),
        )
        paginator = CentralControlPagination()
        page = paginator.paginate_queryset(qs, request)
        serializer = CentralAlertSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class AlertDetailView(APIView):
    """
    GET /api/central-control/alerts/<pk>/
    Requires: central_control.alert.view
    """
    permission_classes = [IsAuthenticated, HasCentralPermission(PERM_ALERT_VIEW)]

    def get(self, request, pk):
        from central_control.selectors import get_alert_by_id
        from central_control.serializers import CentralAlertSerializer

        alert = get_alert_by_id(request.user, pk)
        if alert is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(CentralAlertSerializer(alert).data)


class AlertAcknowledgeView(APIView):
    """
    POST /api/central-control/alerts/<pk>/acknowledge/
    Requires: central_control.alert.acknowledge
    """
    permission_classes = [IsAuthenticated, HasCentralPermission(PERM_ALERT_ACKNOWLEDGE)]

    def post(self, request, pk):
        from central_control.services import AlertService
        from central_control.selectors import get_alert_by_id
        from central_control.serializers import CentralAlertSerializer

        alert = get_alert_by_id(request.user, pk)
        if alert is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        try:
            updated = AlertService.acknowledge_alert(
                actor=request.user,
                alert_id=pk,
                organization=alert.organization,
            )
            return Response(CentralAlertSerializer(updated).data)
        except AlertTransitionError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


class AlertResolveView(APIView):
    """
    POST /api/central-control/alerts/<pk>/resolve/
    Body: {"resolution_note": "..."}
    Requires: central_control.alert.resolve
    """
    permission_classes = [IsAuthenticated, HasCentralPermission(PERM_ALERT_RESOLVE)]

    def post(self, request, pk):
        from central_control.services import AlertService
        from central_control.selectors import get_alert_by_id
        from central_control.serializers import CentralAlertSerializer
        from central_control.exceptions import ResolutionNoteRequiredError

        alert = get_alert_by_id(request.user, pk)
        if alert is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        resolution_note = request.data.get("resolution_note", "")
        try:
            updated = AlertService.resolve_alert(
                actor=request.user,
                alert_id=pk,
                organization=alert.organization,
                resolution_note=resolution_note,
            )
            return Response(CentralAlertSerializer(updated).data)
        except (AlertTransitionError, ResolutionNoteRequiredError) as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


class AlertDismissView(APIView):
    """
    POST /api/central-control/alerts/<pk>/dismiss/
    Body: {"resolution_note": "..."}
    Requires: central_control.alert.dismiss
    """
    permission_classes = [IsAuthenticated, HasCentralPermission(PERM_ALERT_DISMISS)]

    def post(self, request, pk):
        from central_control.services import AlertService
        from central_control.selectors import get_alert_by_id
        from central_control.serializers import CentralAlertSerializer

        alert = get_alert_by_id(request.user, pk)
        if alert is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        try:
            updated = AlertService.dismiss_alert(
                actor=request.user,
                alert_id=pk,
                organization=alert.organization,
                resolution_note=request.data.get("resolution_note", ""),
            )
            return Response(CentralAlertSerializer(updated).data)
        except AlertTransitionError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


# ---------------------------------------------------------------------------
# Issues
# ---------------------------------------------------------------------------

class IssueListCreateView(APIView):
    """
    GET  /api/central-control/issues/       — list with filtering
    POST /api/central-control/issues/       — create new issue
    Requires: central_control.issue.view / central_control.issue.create
    """
    permission_classes = [IsAuthenticated, HasCentralPermission(PERM_ISSUE_VIEW)]

    def get(self, request):
        from central_control.selectors import get_issues_for_user
        from central_control.serializers import CentralIssueSerializer

        qs = get_issues_for_user(
            request.user,
            organization_id=request.query_params.get("organization_id"),
            restaurant_id=request.query_params.get("restaurant_id"),
            branch_id=request.query_params.get("branch_id"),
            severity=request.query_params.get("severity"),
            status=request.query_params.get("status"),
            category=request.query_params.get("category"),
            assigned_to_id=request.query_params.get("assigned_to"),
            search=request.query_params.get("search"),
            ordering=request.query_params.get("ordering", "-created_at"),
        )
        paginator = CentralControlPagination()
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(
            CentralIssueSerializer(page, many=True).data
        )

    def post(self, request):
        from accounts import access as acl
        from central_control.serializers import CentralIssueCreateSerializer, CentralIssueSerializer
        from central_control.issue_services import IssueService

        if not acl.has_permission(request.user, PERM_ISSUE_CREATE):
            return Response(
                {"detail": "You do not have permission to create issues."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = CentralIssueCreateSerializer(
            data=request.data, context={"request": request}
        )
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        vd = serializer.validated_data
        try:
            issue = IssueService.create_issue(
                actor=request.user,
                organization=vd["organization"],
                restaurant=vd.get("restaurant"),
                branch=vd.get("branch"),
                category=vd["category"],
                title=vd["title"],
                description=vd["description"],
                severity=vd["severity"],
                due_at=vd.get("due_at"),
            )
            return Response(CentralIssueSerializer(issue).data, status=status.HTTP_201_CREATED)
        except ScopeViolationError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN)


class IssueDetailView(APIView):
    """
    GET   /api/central-control/issues/<pk>/
    PATCH /api/central-control/issues/<pk>/
    """
    permission_classes = [IsAuthenticated, HasCentralPermission(PERM_ISSUE_VIEW)]

    def get(self, request, pk):
        from central_control.selectors import get_issue_by_id
        from central_control.serializers import CentralIssueSerializer

        issue = get_issue_by_id(request.user, pk)
        if issue is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(CentralIssueSerializer(issue).data)

    def patch(self, request, pk):
        from accounts import access as acl
        from central_control.selectors import get_issue_by_id
        from central_control.serializers import CentralIssueSerializer
        from central_control.issue_services import IssueService

        if not acl.has_permission(request.user, PERM_ISSUE_UPDATE):
            return Response(
                {"detail": "Permission denied."}, status=status.HTTP_403_FORBIDDEN
            )

        issue = get_issue_by_id(request.user, pk)
        if issue is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        try:
            updated = IssueService.update_issue(
                actor=request.user,
                issue_id=pk,
                organization=issue.organization,
                **{k: v for k, v in request.data.items()
                   if k in ("title", "description", "severity", "due_at")},
            )
            return Response(CentralIssueSerializer(updated).data)
        except (IssueImmutableError, IssueTransitionError) as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


class IssueAssignView(APIView):
    """POST /api/central-control/issues/<pk>/assign/"""
    permission_classes = [IsAuthenticated, HasCentralPermission(PERM_ISSUE_ASSIGN)]

    def post(self, request, pk):
        from django.contrib.auth import get_user_model
        from central_control.selectors import get_issue_by_id
        from central_control.serializers import CentralIssueSerializer
        from central_control.issue_services import IssueService

        issue = get_issue_by_id(request.user, pk)
        if issue is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        assignee_id = request.data.get("assignee_id")
        if not assignee_id:
            return Response(
                {"detail": "assignee_id is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        User = get_user_model()
        try:
            assignee = User.objects.get(pk=assignee_id, is_active=True)
        except User.DoesNotExist:
            return Response(
                {"detail": "Assignee not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            updated = IssueService.assign_issue(
                actor=request.user,
                issue_id=pk,
                organization=issue.organization,
                assignee_user=assignee,
            )
            return Response(CentralIssueSerializer(updated).data)
        except (IssueNotFoundError, IssueImmutableError, IssueAssignmentScopeError) as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


class IssueStartView(APIView):
    """POST /api/central-control/issues/<pk>/start/"""
    permission_classes = [IsAuthenticated, HasCentralPermission(PERM_ISSUE_UPDATE)]

    def post(self, request, pk):
        from central_control.selectors import get_issue_by_id
        from central_control.serializers import CentralIssueSerializer
        from central_control.issue_services import IssueService

        issue = get_issue_by_id(request.user, pk)
        if issue is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        try:
            updated = IssueService.start_issue(
                actor=request.user, issue_id=pk, organization=issue.organization
            )
            return Response(CentralIssueSerializer(updated).data)
        except (IssueTransitionError, IssueImmutableError) as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


class IssueResolveView(APIView):
    """POST /api/central-control/issues/<pk>/resolve/"""
    permission_classes = [IsAuthenticated, HasCentralPermission(PERM_ISSUE_RESOLVE)]

    def post(self, request, pk):
        from central_control.selectors import get_issue_by_id
        from central_control.serializers import CentralIssueSerializer
        from central_control.issue_services import IssueService

        issue = get_issue_by_id(request.user, pk)
        if issue is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        resolution_note = request.data.get("resolution_note", "")
        try:
            updated = IssueService.resolve_issue(
                actor=request.user,
                issue_id=pk,
                organization=issue.organization,
                resolution_note=resolution_note,
            )
            return Response(CentralIssueSerializer(updated).data)
        except (IssueTransitionError, IssueImmutableError, ResolutionNoteRequiredError) as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


class IssueCloseView(APIView):
    """POST /api/central-control/issues/<pk>/close/"""
    permission_classes = [IsAuthenticated, HasCentralPermission(PERM_ISSUE_CLOSE)]

    def post(self, request, pk):
        from central_control.selectors import get_issue_by_id
        from central_control.serializers import CentralIssueSerializer
        from central_control.issue_services import IssueService

        issue = get_issue_by_id(request.user, pk)
        if issue is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        try:
            updated = IssueService.close_issue(
                actor=request.user, issue_id=pk, organization=issue.organization
            )
            return Response(CentralIssueSerializer(updated).data)
        except (IssueTransitionError, IssueImmutableError) as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


class IssueCancelView(APIView):
    """POST /api/central-control/issues/<pk>/cancel/"""
    permission_classes = [IsAuthenticated, HasCentralPermission(PERM_ISSUE_UPDATE)]

    def post(self, request, pk):
        from central_control.selectors import get_issue_by_id
        from central_control.serializers import CentralIssueSerializer
        from central_control.issue_services import IssueService

        issue = get_issue_by_id(request.user, pk)
        if issue is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        try:
            updated = IssueService.cancel_issue(
                actor=request.user,
                issue_id=pk,
                organization=issue.organization,
                reason=request.data.get("reason", ""),
            )
            return Response(CentralIssueSerializer(updated).data)
        except (IssueTransitionError, IssueImmutableError) as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


# ---------------------------------------------------------------------------
# Event Timeline
# ---------------------------------------------------------------------------

class EventTimelineView(APIView):
    """
    GET /api/central-control/events/
    Requires: central_control.system_event.view
    """
    permission_classes = [IsAuthenticated, HasCentralPermission(PERM_SYSTEM_EVENT_VIEW)]

    def get(self, request):
        from central_control.selectors import get_events_for_user
        from central_control.serializers import CentralSystemEventSerializer

        qs = get_events_for_user(
            request.user,
            organization_id=request.query_params.get("organization_id"),
            restaurant_id=request.query_params.get("restaurant_id"),
            branch_id=request.query_params.get("branch_id"),
            event_type=request.query_params.get("event_type"),
            severity=request.query_params.get("severity"),
            search=request.query_params.get("search"),
        )
        paginator = CentralControlPagination()
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(
            CentralSystemEventSerializer(page, many=True).data
        )


# ---------------------------------------------------------------------------
# System Health
# ---------------------------------------------------------------------------

class SystemHealthView(APIView):
    """
    GET /api/central-control/system-health/
    Returns safe application-level health without exposing secrets.
    Requires: central_control.health.view
    """
    permission_classes = [IsAuthenticated, HasCentralPermission(PERM_HEALTH_VIEW)]

    def get(self, request):
        from central_control.dashboard_services import get_system_health
        try:
            data = get_system_health()
            return Response(data)
        except Exception as exc:
            logger.error("SystemHealthView error: %s", exc, exc_info=True)
            return Response(
                {"overall": "UNKNOWN", "error": "Health check unavailable."},
                status=status.HTTP_200_OK,
            )


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

class CentralSettingsView(APIView):
    """
    GET   /api/central-control/settings/
    PATCH /api/central-control/settings/
    Requires: central_control.configuration.view / .manage
    """
    permission_classes = [IsAuthenticated, HasCentralPermission(PERM_CONFIGURATION_VIEW)]

    def get(self, request):
        from central_control.selectors import get_settings_for_organization
        from central_control.serializers import CentralControlSettingsSerializer
        from accounts import access as acl

        org = acl.get_accessible_organizations(request.user).first()
        if org is None:
            return Response({"detail": "No accessible organization."}, status=status.HTTP_403_FORBIDDEN)

        settings_obj = get_settings_for_organization(org)
        return Response(CentralControlSettingsSerializer(settings_obj).data)

    def patch(self, request):
        from central_control.selectors import get_settings_for_organization
        from central_control.serializers import CentralControlSettingsSerializer
        from central_control.services import record_audit_entry
        from central_control.constants import AUDIT_CONFIGURATION_UPDATED
        from accounts import access as acl

        if not acl.has_permission(request.user, PERM_CONFIGURATION_MANAGE):
            return Response({"detail": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)

        org = acl.get_accessible_organizations(request.user).first()
        if org is None:
            return Response({"detail": "No accessible organization."}, status=status.HTTP_403_FORBIDDEN)

        settings_obj = get_settings_for_organization(org)
        serializer = CentralControlSettingsSerializer(
            settings_obj, data=request.data, partial=True
        )
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        serializer.save()
        record_audit_entry(
            actor=request.user,
            action=AUDIT_CONFIGURATION_UPDATED,
            entity_type="SETTINGS",
            entity_id=settings_obj.pk,
            organization=org,
            metadata=request.data,
        )
        return Response(serializer.data)


# ---------------------------------------------------------------------------
# Audit Log
# ---------------------------------------------------------------------------

class AuditLogView(APIView):
    """
    GET /api/central-control/audit/
    Requires: central_control.audit.view
    """
    permission_classes = [IsAuthenticated, HasCentralPermission(PERM_AUDIT_VIEW)]

    def get(self, request):
        from central_control.selectors import get_audit_logs_for_user
        from central_control.serializers import CentralControlAuditLogSerializer

        qs = get_audit_logs_for_user(
            request.user,
            organization_id=request.query_params.get("organization_id"),
            entity_type=request.query_params.get("entity_type"),
            entity_id=request.query_params.get("entity_id"),
        )
        paginator = CentralControlPagination()
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(
            CentralControlAuditLogSerializer(page, many=True).data
        )


# ---------------------------------------------------------------------------
# User Access Monitoring
# ---------------------------------------------------------------------------

class UserAccessView(APIView):
    """
    GET /api/central-control/users/
    Read-only visibility into users in scope.
    Requires: central_control.user_access.view
    """
    permission_classes = [IsAuthenticated, HasCentralPermission(PERM_USER_ACCESS_VIEW)]

    def get(self, request):
        from central_control.selectors import get_users_for_central_control
        from central_control.serializers import CentralUserSummarySerializer

        qs = get_users_for_central_control(
            request.user,
            organization_id=request.query_params.get("organization_id"),
            search=request.query_params.get("search"),
        )
        paginator = CentralControlPagination()
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(
            CentralUserSummarySerializer(page, many=True).data
        )


# ---------------------------------------------------------------------------
# Admin: run alert detection manually
# ---------------------------------------------------------------------------

class RunDetectionView(APIView):
    """
    POST /api/central-control/run-detection/
    Triggers alert detection for the user's organization.
    Restricted to staff or superusers.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not (request.user.is_staff or request.user.is_superuser):
            return Response({"detail": "Admin only."}, status=status.HTTP_403_FORBIDDEN)

        from accounts import access as acl
        from central_control.alert_rules import AlertDetectionService, EscalationEngine

        results = {}
        for org in acl.get_accessible_organizations(request.user):
            svc = AlertDetectionService(org)
            org_result = svc.run_all()

            esc = EscalationEngine(org)
            try:
                esc.run()
                org_result["escalation"] = "ok"
            except Exception as exc:
                org_result["escalation"] = f"error: {exc}"

            results[str(org.pk)] = org_result

        return Response({"results": results})
