# =============================================================================
# RestaurantFlow — Counters Views
# Phase 4
#
# URL layout:
#   GET    /api/counters/                          list
#   POST   /api/counters/                          create
#   GET    /api/counters/<id>/                     retrieve
#   PATCH  /api/counters/<id>/                     partial update
#   POST   /api/counters/<id>/disable/             disable
#   POST   /api/counters/<id>/reactivate/          reactivate
#   POST   /api/counters/<id>/sessions/open/       open session
#
#   GET    /api/counter-assignments/               list
#   POST   /api/counter-assignments/               create
#   GET    /api/counter-assignments/<id>/          retrieve
#   PATCH  /api/counter-assignments/<id>/          update
#   POST   /api/counter-assignments/<id>/deactivate/ deactivate
#
#   GET    /api/counter-sessions/                  list
#   GET    /api/counter-sessions/<id>/             retrieve
#   POST   /api/counter-sessions/<id>/close/       close
#   POST   /api/counter-sessions/<id>/force-close/ force close
#
#   GET    /api/shifts/                            list
#   POST   /api/shifts/                            create
#   GET    /api/shifts/<id>/                       retrieve
#   PATCH  /api/shifts/<id>/                       update
#
#   GET    /api/counter-dashboard/                 branch dashboard
#
# Security:
#   All views use scoped querysets; get_object() returns 404 (not 403)
#   for resources the user cannot access — prevents UUID enumeration.
# =============================================================================

import logging
from rest_framework import generics, status
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts import access as acl
from accounts.permissions import HasPermission

from counters import access as counter_acl
from counters import services
from counters.models import Counter, CounterAssignment, CounterSession, Shift
from counters.permissions import HasCounterAccess, HasCounterSessionAccess
from counters.serializers import (
    CounterSerializer,
    CounterDetailSerializer,
    CounterAssignmentSerializer,
    CounterSessionSerializer,
    ShiftSerializer,
    OpenSessionSerializer,
    CloseSessionSerializer,
    ForceCloseSessionSerializer,
)

logger = logging.getLogger("counters")


# =============================================================================
# Helpers
# =============================================================================

def _error(code, message, http_status=400):
    return Response(
        {"error": {"code": code, "message": message}},
        status=http_status,
    )


# =============================================================================
# Counter views
# =============================================================================

class CounterListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/counters/   — list counters scoped to user
    POST /api/counters/   — create a counter (requires counter.create)
    """

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated(), HasPermission("counter.create")()]
        return [IsAuthenticated(), HasPermission("counter.view")()]

    def get_serializer_class(self):
        return CounterSerializer

    def get_queryset(self):
        qs = counter_acl.get_accessible_counters(self.request.user)
        # Optional filters
        branch_id = self.request.query_params.get("branch")
        status_filter = self.request.query_params.get("status")
        if branch_id:
            qs = qs.filter(branch_id=branch_id)
        if status_filter:
            qs = qs.filter(status=status_filter.upper())
        return qs

    def perform_create(self, serializer):
        branch = serializer.validated_data.get("branch")
        if branch and not acl.can_access_branch(self.request.user, branch):
            raise PermissionDenied("You do not have access to the specified branch.")
        counter = serializer.save()
        logger.info(
            "Counter created: %s/%s (id=%s) by user=%s",
            counter.branch.name,
            counter.code,
            counter.id,
            self.request.user.email,
        )


class CounterDetailView(generics.RetrieveUpdateAPIView):
    """
    GET   /api/counters/<id>/   — retrieve (scoped)
    PATCH /api/counters/<id>/   — partial update (requires counter.update)
    """

    http_method_names = ["get", "patch", "head", "options"]

    def get_permissions(self):
        if self.request.method == "PATCH":
            return [
                IsAuthenticated(),
                HasPermission("counter.update")(),
                HasCounterAccess(),
            ]
        return [IsAuthenticated(), HasPermission("counter.view")(), HasCounterAccess()]

    def get_serializer_class(self):
        if self.request.method == "GET":
            return CounterDetailSerializer
        return CounterSerializer

    def get_queryset(self):
        return counter_acl.get_accessible_counters(self.request.user)

    def perform_update(self, serializer):
        counter = serializer.save()
        logger.info(
            "Counter updated: %s (id=%s) by user=%s",
            counter.code,
            counter.id,
            self.request.user.email,
        )


class CounterDisableView(APIView):
    """POST /api/counters/<id>/disable/"""

    permission_classes = [IsAuthenticated, HasPermission("counter.disable")]

    def post(self, request, pk):
        try:
            counter = counter_acl.get_accessible_counters(request.user).get(pk=pk)
        except Counter.DoesNotExist:
            raise NotFound("Counter not found.")

        try:
            counter = services.disable_counter(request.user, counter=counter)
        except PermissionDenied as e:
            return _error("COUNTER_ACCESS_DENIED", str(e), 403)

        return Response(CounterSerializer(counter).data)


class CounterReactivateView(APIView):
    """POST /api/counters/<id>/reactivate/"""

    permission_classes = [IsAuthenticated, HasPermission("counter.update")]

    def post(self, request, pk):
        try:
            counter = counter_acl.get_accessible_counters(request.user).get(pk=pk)
        except Counter.DoesNotExist:
            raise NotFound("Counter not found.")

        try:
            counter = services.reactivate_counter(request.user, counter=counter)
        except PermissionDenied as e:
            return _error("COUNTER_ACCESS_DENIED", str(e), 403)

        return Response(CounterSerializer(counter).data)


# =============================================================================
# Counter Session — open (nested under counter)
# =============================================================================

class CounterOpenSessionView(APIView):
    """
    POST /api/counters/<pk>/sessions/open/

    Body: { "opening_cash": "5000.00", "shift": "<uuid>" (optional) }
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            counter = counter_acl.get_accessible_counters(request.user).get(pk=pk)
        except Counter.DoesNotExist:
            raise NotFound("Counter not found.")

        serializer = OpenSessionSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"error": True, "message": "Validation error.", "details": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            session = services.open_session(
                request.user,
                counter=counter,
                opening_cash=serializer.validated_data["opening_cash"],
                shift=serializer.validated_data.get("shift"),
            )
        except PermissionDenied as e:
            return _error("COUNTER_ACCESS_DENIED", str(e), 403)
        except Exception as e:
            err = getattr(e, "detail", None)
            if isinstance(err, dict) and "code" in err:
                return _error(err["code"], err["message"])
            return _error("SESSION_OPEN_FAILED", str(e))

        return Response(
            CounterSessionSerializer(session).data,
            status=status.HTTP_201_CREATED,
        )


# =============================================================================
# Counter Sessions — standalone
# =============================================================================

class CounterSessionListView(generics.ListAPIView):
    """
    GET /api/counter-sessions/

    Optional filters: counter=<uuid>, status=OPEN|CLOSED|FORCE_CLOSED,
                      branch=<uuid>
    """

    permission_classes = [IsAuthenticated, HasPermission("counter.session.view")]
    serializer_class = CounterSessionSerializer

    def get_queryset(self):
        qs = counter_acl.get_accessible_sessions(self.request.user)
        counter_id = self.request.query_params.get("counter")
        status_filter = self.request.query_params.get("status")
        branch_id = self.request.query_params.get("branch")
        if counter_id:
            qs = qs.filter(counter_id=counter_id)
        if status_filter:
            qs = qs.filter(status=status_filter.upper())
        if branch_id:
            qs = qs.filter(counter__branch_id=branch_id)
        return qs


class CounterSessionDetailView(generics.RetrieveAPIView):
    """GET /api/counter-sessions/<id>/"""

    permission_classes = [
        IsAuthenticated,
        HasPermission("counter.session.view"),
        HasCounterSessionAccess,
    ]
    serializer_class = CounterSessionSerializer

    def get_queryset(self):
        return counter_acl.get_accessible_sessions(self.request.user)


class CounterSessionCloseView(APIView):
    """
    POST /api/counter-sessions/<id>/close/

    Body: { "actual_cash": "9850.00", "closing_note": "..." }
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            session = counter_acl.get_accessible_sessions(request.user).get(pk=pk)
        except CounterSession.DoesNotExist:
            raise NotFound("Counter session not found.")

        serializer = CloseSessionSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"error": True, "message": "Validation error.", "details": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            session = services.close_session(
                request.user,
                session=session,
                actual_cash=serializer.validated_data["actual_cash"],
                closing_note=serializer.validated_data.get("closing_note", ""),
            )
        except PermissionDenied as e:
            return _error("COUNTER_ACCESS_DENIED", str(e), 403)
        except Exception as e:
            err = getattr(e, "detail", None)
            if isinstance(err, dict) and "code" in err:
                return _error(err["code"], err["message"])
            return _error("SESSION_CLOSE_FAILED", str(e))

        return Response(CounterSessionSerializer(session).data)


class CounterSessionForceCloseView(APIView):
    """
    POST /api/counter-sessions/<id>/force-close/

    Body: { "actual_cash": "9850.00" (optional), "reason": "..." }
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            session = counter_acl.get_accessible_sessions(request.user).get(pk=pk)
        except CounterSession.DoesNotExist:
            raise NotFound("Counter session not found.")

        serializer = ForceCloseSessionSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"error": True, "message": "Validation error.", "details": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            session = services.force_close_session(
                request.user,
                session=session,
                actual_cash=serializer.validated_data.get("actual_cash"),
                reason=serializer.validated_data.get("reason", ""),
            )
        except PermissionDenied as e:
            return _error("FORCE_CLOSE_NOT_ALLOWED", str(e), 403)
        except Exception as e:
            err = getattr(e, "detail", None)
            if isinstance(err, dict) and "code" in err:
                return _error(err["code"], err["message"])
            return _error("SESSION_FORCE_CLOSE_FAILED", str(e))

        return Response(CounterSessionSerializer(session).data)


# =============================================================================
# Counter Assignments
# =============================================================================

class CounterAssignmentListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/counter-assignments/   — list
    POST /api/counter-assignments/   — create
    """

    serializer_class = CounterAssignmentSerializer

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated(), HasPermission("counter.assign")()]
        return [IsAuthenticated(), HasPermission("counter.view")()]

    def get_queryset(self):
        qs = counter_acl.get_accessible_assignments(self.request.user)
        counter_id = self.request.query_params.get("counter")
        is_active = self.request.query_params.get("is_active")
        if counter_id:
            qs = qs.filter(counter_id=counter_id)
        if is_active is not None:
            qs = qs.filter(is_active=is_active.lower() == "true")
        return qs

    def perform_create(self, serializer):
        counter = serializer.validated_data["counter"]
        user = serializer.validated_data["user"]
        expires_at = serializer.validated_data.get("expires_at")

        try:
            assignment = services.assign_counter(
                self.request.user,
                counter=counter,
                user=user,
                expires_at=expires_at,
            )
        except PermissionDenied as e:
            raise PermissionDenied(str(e))
        except Exception as e:
            from rest_framework.exceptions import ValidationError
            raise ValidationError(str(e))

        # Return the created object (serializer.save() not called — service handles it)
        # Override: re-bind the instance to the serializer so DRF can respond
        serializer.instance = assignment


class CounterAssignmentDetailView(generics.RetrieveUpdateAPIView):
    """
    GET   /api/counter-assignments/<id>/
    PATCH /api/counter-assignments/<id>/
    """

    serializer_class = CounterAssignmentSerializer
    http_method_names = ["get", "patch", "head", "options"]

    def get_permissions(self):
        if self.request.method == "PATCH":
            return [IsAuthenticated(), HasPermission("counter.assign")()]
        return [IsAuthenticated(), HasPermission("counter.view")()]

    def get_queryset(self):
        return counter_acl.get_accessible_assignments(self.request.user)


class CounterAssignmentDeactivateView(APIView):
    """POST /api/counter-assignments/<id>/deactivate/"""

    permission_classes = [IsAuthenticated, HasPermission("counter.unassign")]

    def post(self, request, pk):
        try:
            assignment = counter_acl.get_accessible_assignments(request.user).get(pk=pk)
        except CounterAssignment.DoesNotExist:
            raise NotFound("Counter assignment not found.")

        try:
            assignment = services.deactivate_assignment(request.user, assignment=assignment)
        except PermissionDenied as e:
            return _error("COUNTER_ACCESS_DENIED", str(e), 403)

        return Response(CounterAssignmentSerializer(assignment).data)


# =============================================================================
# Shifts
# =============================================================================

class ShiftListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/shifts/
    POST /api/shifts/
    """

    serializer_class = ShiftSerializer

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated(), HasPermission("shift.manage")()]
        return [IsAuthenticated(), HasPermission("shift.view")()]

    def get_queryset(self):
        qs = counter_acl.get_accessible_shifts(self.request.user)
        branch_id = self.request.query_params.get("branch")
        if branch_id:
            qs = qs.filter(branch_id=branch_id)
        return qs

    def perform_create(self, serializer):
        branch = serializer.validated_data.get("branch")
        if branch and not acl.can_access_branch(self.request.user, branch):
            raise PermissionDenied("You do not have access to the specified branch.")
        serializer.save()


class ShiftDetailView(generics.RetrieveUpdateAPIView):
    """
    GET   /api/shifts/<id>/
    PATCH /api/shifts/<id>/
    """

    serializer_class = ShiftSerializer
    http_method_names = ["get", "patch", "head", "options"]

    def get_permissions(self):
        if self.request.method == "PATCH":
            return [IsAuthenticated(), HasPermission("shift.manage")()]
        return [IsAuthenticated(), HasPermission("shift.view")()]

    def get_queryset(self):
        return counter_acl.get_accessible_shifts(self.request.user)


# =============================================================================
# Counter Dashboard
# =============================================================================

class CounterDashboardView(APIView):
    """
    GET /api/counter-dashboard/?branch=<uuid>

    Returns a branch-level summary of all counters with their current
    session status.
    """

    permission_classes = [IsAuthenticated, HasPermission("counter.view")]

    def get(self, request):
        branch_id = request.query_params.get("branch")
        counters_qs = counter_acl.get_accessible_counters(request.user).prefetch_related(
            "sessions", "assignments__user"
        )
        if branch_id:
            counters_qs = counters_qs.filter(branch_id=branch_id)

        data = []
        for counter in counters_qs:
            open_session = counter.sessions.filter(status="OPEN").select_related("opened_by").first()
            active_assignment = counter.assignments.filter(is_active=True).select_related("user").first()

            data.append({
                "id": str(counter.id),
                "code": counter.code,
                "name": counter.name,
                "counter_type": counter.counter_type,
                "status": counter.status,
                "branch_id": str(counter.branch_id),
                "branch_name": counter.branch.name,
                "restaurant_name": counter.branch.restaurant.name,
                "current_session": {
                    "id": str(open_session.id),
                    "opened_by_email": open_session.opened_by.email,
                    "opened_by_name": open_session.opened_by.full_name,
                    "opened_at": open_session.opened_at.isoformat(),
                    "opening_cash": str(open_session.opening_cash),
                    "status": open_session.status,
                } if open_session else None,
                "assigned_cashier": {
                    "user_id": active_assignment.user.id,
                    "user_name": active_assignment.user.full_name,
                    "user_email": active_assignment.user.email,
                } if active_assignment else None,
            })

        return Response({
            "branch_id": branch_id,
            "counters": data,
            "summary": {
                "total": len(data),
                "active": sum(1 for c in data if c["status"] == "ACTIVE"),
                "sessions_open": sum(1 for c in data if c["current_session"] is not None),
                "inactive": sum(1 for c in data if c["status"] == "INACTIVE"),
                "maintenance": sum(1 for c in data if c["status"] == "MAINTENANCE"),
            },
        })
