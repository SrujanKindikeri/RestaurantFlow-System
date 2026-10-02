# =============================================================================
# RestaurantFlow — Counters Serializers
# Phase 4
# =============================================================================

import logging
from decimal import Decimal, InvalidOperation

from rest_framework import serializers

from accounts.models import User
from accounts import access as acl
from .models import Counter, CounterAssignment, Shift, CounterSession, CounterStatus

logger = logging.getLogger("counters")


# =============================================================================
# Shift
# =============================================================================

class ShiftSerializer(serializers.ModelSerializer):
    branch_name = serializers.CharField(source="branch.name", read_only=True)

    class Meta:
        model = Shift
        fields = [
            "id", "branch", "branch_name",
            "name", "start_time", "end_time",
            "is_active", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "branch_name", "created_at", "updated_at"]


# =============================================================================
# Counter
# =============================================================================

class CounterSerializer(serializers.ModelSerializer):
    """
    Flat Counter representation used in list and write contexts.
    """
    branch_name     = serializers.CharField(source="branch.name", read_only=True)
    restaurant_id   = serializers.UUIDField(
        source="branch.restaurant.id", read_only=True
    )
    restaurant_name = serializers.CharField(
        source="branch.restaurant.name", read_only=True
    )
    organization_id = serializers.UUIDField(
        source="branch.restaurant.organization.id", read_only=True
    )

    class Meta:
        model = Counter
        fields = [
            "id", "branch", "branch_name",
            "restaurant_id", "restaurant_name", "organization_id",
            "name", "code", "description",
            "counter_type", "location",
            "status", "is_active",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "is_active",
            "branch_name", "restaurant_id", "restaurant_name", "organization_id",
            "created_at", "updated_at",
        ]

    def validate_code(self, value):
        return value.strip().upper()

    def validate(self, attrs):
        branch = attrs.get("branch") or (
            self.instance.branch if self.instance else None
        )
        code = attrs.get("code", self.instance.code if self.instance else None)

        if branch and code:
            qs = Counter.objects.filter(
                branch=branch, code=code.strip().upper()
            )
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError(
                    {"code": f"A counter with code '{code}' already exists in branch '{branch.name}'."}
                )

        return attrs


class CounterDetailSerializer(CounterSerializer):
    """Counter with embedded current session summary."""

    current_session = serializers.SerializerMethodField()
    active_assignments = serializers.SerializerMethodField()

    class Meta(CounterSerializer.Meta):
        fields = CounterSerializer.Meta.fields + ["current_session", "active_assignments"]

    def get_current_session(self, obj):
        session = obj.sessions.filter(status="OPEN").select_related("opened_by").first()
        if not session:
            return None
        return {
            "id": str(session.id),
            "opened_by_email": session.opened_by.email,
            "opened_by_name": session.opened_by.full_name,
            "opened_at": session.opened_at,
            "opening_cash": str(session.opening_cash),
            "expected_cash": str(session.expected_cash),
            "status": session.status,
        }

    def get_active_assignments(self, obj):
        assignments = (
            obj.assignments.filter(is_active=True)
            .select_related("user")
        )
        return [
            {
                "id": str(a.id),
                "user_id": a.user.id,
                "user_email": a.user.email,
                "user_name": a.user.full_name,
                "assigned_at": a.assigned_at,
                "expires_at": a.expires_at,
            }
            for a in assignments
        ]


# =============================================================================
# CounterAssignment
# =============================================================================

class CounterAssignmentSerializer(serializers.ModelSerializer):
    counter_code   = serializers.CharField(source="counter.code", read_only=True)
    counter_name   = serializers.CharField(source="counter.name", read_only=True)
    branch_id      = serializers.UUIDField(source="counter.branch.id", read_only=True)
    branch_name    = serializers.CharField(source="counter.branch.name", read_only=True)
    user_email     = serializers.CharField(source="user.email", read_only=True)
    user_name      = serializers.CharField(source="user.full_name", read_only=True)
    assigned_by_email = serializers.SerializerMethodField()

    class Meta:
        model = CounterAssignment
        fields = [
            "id",
            "counter", "counter_code", "counter_name",
            "branch_id", "branch_name",
            "user", "user_email", "user_name",
            "assigned_by", "assigned_by_email",
            "assigned_at", "expires_at",
            "is_active",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "assigned_at",
            "counter_code", "counter_name",
            "branch_id", "branch_name",
            "user_email", "user_name",
            "assigned_by", "assigned_by_email",
            "created_at", "updated_at",
        ]

    def get_assigned_by_email(self, obj):
        return obj.assigned_by.email if obj.assigned_by else None

    def validate(self, attrs):
        counter = attrs.get("counter") or (
            self.instance.counter if self.instance else None
        )
        user = attrs.get("user") or (
            self.instance.user if self.instance else None
        )

        if not counter or not user:
            return attrs

        # Validate the user can access this counter's branch.
        # We do this by checking the user has at least one active assignment
        # to the counter's branch (or higher scope).
        if not acl.can_access_branch(user, counter.branch):
            raise serializers.ValidationError(
                {
                    "user": (
                        f"User '{user.email}' does not have access to branch "
                        f"'{counter.branch.name}'. Cannot assign to this counter."
                    )
                }
            )

        return attrs


# =============================================================================
# CounterSession
# =============================================================================

class CounterSessionSerializer(serializers.ModelSerializer):
    """
    Read serializer for CounterSession — used for list and retrieve.
    """
    counter_code    = serializers.CharField(source="counter.code", read_only=True)
    counter_name    = serializers.CharField(source="counter.name", read_only=True)
    branch_id       = serializers.UUIDField(source="counter.branch.id", read_only=True)
    branch_name     = serializers.CharField(source="counter.branch.name", read_only=True)
    restaurant_name = serializers.CharField(
        source="counter.branch.restaurant.name", read_only=True
    )
    opened_by_email = serializers.CharField(source="opened_by.email", read_only=True)
    opened_by_name  = serializers.CharField(source="opened_by.full_name", read_only=True)
    closed_by_email = serializers.SerializerMethodField()
    shift_name      = serializers.SerializerMethodField()

    class Meta:
        model = CounterSession
        fields = [
            "id",
            "counter", "counter_code", "counter_name",
            "branch_id", "branch_name", "restaurant_name",
            "shift", "shift_name",
            "opened_by", "opened_by_email", "opened_by_name",
            "closed_by", "closed_by_email",
            "opened_at", "closed_at",
            "opening_cash", "expected_cash",
            "actual_cash", "cash_difference",
            "status", "closing_note",
            "created_at", "updated_at",
        ]
        read_only_fields = fields  # All fields are read-only on this serializer

    def get_closed_by_email(self, obj):
        return obj.closed_by.email if obj.closed_by else None

    def get_shift_name(self, obj):
        return obj.shift.name if obj.shift else None


class OpenSessionSerializer(serializers.Serializer):
    """
    Write serializer for opening a counter session.

    POST /api/counters/{id}/sessions/open/
    """
    opening_cash = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal("0.00"),
    )
    shift = serializers.PrimaryKeyRelatedField(
        queryset=Shift.objects.filter(is_active=True),
        required=False,
        allow_null=True,
        default=None,
    )

    def validate_opening_cash(self, value):
        try:
            value = Decimal(str(value))
        except InvalidOperation:
            raise serializers.ValidationError("Invalid opening cash amount.")
        if value < Decimal("0.00"):
            raise serializers.ValidationError("Opening cash cannot be negative.")
        return value


class CloseSessionSerializer(serializers.Serializer):
    """
    Write serializer for closing a counter session.

    POST /api/counter-sessions/{id}/close/
    """
    actual_cash = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal("0.00"),
    )
    closing_note = serializers.CharField(required=False, allow_blank=True, default="")

    def validate_actual_cash(self, value):
        try:
            value = Decimal(str(value))
        except InvalidOperation:
            raise serializers.ValidationError("Invalid actual cash amount.")
        if value < Decimal("0.00"):
            raise serializers.ValidationError("Actual cash cannot be negative.")
        return value


class ForceCloseSessionSerializer(serializers.Serializer):
    """
    Write serializer for force-closing a counter session.

    POST /api/counter-sessions/{id}/force-close/
    """
    actual_cash = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal("0.00"),
        required=False,
        allow_null=True,
        default=None,
    )
    reason = serializers.CharField(min_length=1)

    def validate_actual_cash(self, value):
        if value is None:
            return value
        try:
            value = Decimal(str(value))
        except InvalidOperation:
            raise serializers.ValidationError("Invalid actual cash amount.")
        if value < Decimal("0.00"):
            raise serializers.ValidationError("Actual cash cannot be negative.")
        return value
