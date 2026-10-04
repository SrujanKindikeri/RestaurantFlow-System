# =============================================================================
# RestaurantFlow — Central Control Center Serializers
# Phase 15
#
# Serializers are thin: they validate input and shape output.
# Business logic remains in services/selectors.
# Never trust frontend-computed financial values.
# =============================================================================

from rest_framework import serializers

from central_control.models import (
    CentralControlSettings,
    CentralAlert,
    EscalationRule,
    CentralIssue,
    CentralSystemEvent,
    CentralControlAuditLog,
)
from central_control.constants import (
    ALERT_TYPE_CHOICES, ALERT_SEVERITY_CHOICES, ALERT_STATUS_CHOICES,
    ISSUE_CATEGORY_CHOICES, ISSUE_SEVERITY_CHOICES, ISSUE_STATUS_CHOICES,
)


# ---------------------------------------------------------------------------
# Nested mini serializers
# ---------------------------------------------------------------------------

class OrganizationMiniSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()


class RestaurantMiniSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    is_active = serializers.BooleanField()


class BranchMiniSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    is_active = serializers.BooleanField()


class UserMiniSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    email = serializers.EmailField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()

    def to_representation(self, instance):
        if instance is None:
            return None
        return {
            "id": instance.pk,
            "email": instance.email,
            "first_name": instance.first_name,
            "last_name": instance.last_name,
        }


# ---------------------------------------------------------------------------
# CentralControlSettings
# ---------------------------------------------------------------------------

class CentralControlSettingsSerializer(serializers.ModelSerializer):
    organization_id = serializers.UUIDField(source="organization.pk", read_only=True)
    organization_name = serializers.CharField(source="organization.name", read_only=True)

    class Meta:
        model = CentralControlSettings
        fields = [
            "id", "organization_id", "organization_name",
            "kitchen_delay_minutes", "kitchen_backlog_threshold",
            "low_stock_alert_enabled", "out_of_stock_alert_enabled",
            "payable_overdue_alert_enabled", "payment_failure_threshold",
            "counter_session_max_hours",
            "alert_escalation_enabled", "issue_auto_creation_enabled",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "organization_id", "organization_name", "created_at", "updated_at"]

    def validate_kitchen_delay_minutes(self, value):
        if value < 1 or value > 480:
            raise serializers.ValidationError("Must be 1–480.")
        return value

    def validate_kitchen_backlog_threshold(self, value):
        if value < 1 or value > 500:
            raise serializers.ValidationError("Must be 1–500.")
        return value

    def validate_payment_failure_threshold(self, value):
        if value < 1 or value > 1000:
            raise serializers.ValidationError("Must be 1–1000.")
        return value


# ---------------------------------------------------------------------------
# CentralAlert
# ---------------------------------------------------------------------------

class CentralAlertSerializer(serializers.ModelSerializer):
    organization = OrganizationMiniSerializer(read_only=True)
    restaurant = RestaurantMiniSerializer(read_only=True)
    branch = BranchMiniSerializer(read_only=True)
    acknowledged_by = UserMiniSerializer(read_only=True)
    resolved_by = UserMiniSerializer(read_only=True)

    class Meta:
        model = CentralAlert
        fields = [
            "id", "organization", "restaurant", "branch",
            "alert_type", "severity", "title", "message",
            "source_type", "source_id",
            "status",
            "detected_at", "expires_at",
            "acknowledged_at", "acknowledged_by",
            "resolved_at", "resolved_by", "resolution_note",
            "detection_count", "last_detected_at",
            "created_at", "updated_at",
        ]
        read_only_fields = fields


# ---------------------------------------------------------------------------
# EscalationRule
# ---------------------------------------------------------------------------

class EscalationRuleSerializer(serializers.ModelSerializer):
    restaurant = RestaurantMiniSerializer(read_only=True)
    organization_id = serializers.UUIDField(source="organization.pk", read_only=True)

    class Meta:
        model = EscalationRule
        fields = [
            "id", "organization_id", "restaurant",
            "alert_type", "severity", "threshold_minutes",
            "auto_create_issue", "escalation_target_role",
            "is_active", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


# ---------------------------------------------------------------------------
# CentralIssue
# ---------------------------------------------------------------------------

class CentralIssueSerializer(serializers.ModelSerializer):
    organization = OrganizationMiniSerializer(read_only=True)
    restaurant = RestaurantMiniSerializer(read_only=True)
    branch = BranchMiniSerializer(read_only=True)
    created_by = UserMiniSerializer(read_only=True)
    assigned_to = UserMiniSerializer(read_only=True)
    resolved_by = UserMiniSerializer(read_only=True)
    closed_by = UserMiniSerializer(read_only=True)
    detected_from_alert_id = serializers.UUIDField(
        source="detected_from_alert.pk", read_only=True, allow_null=True
    )

    class Meta:
        model = CentralIssue
        fields = [
            "id", "organization", "restaurant", "branch",
            "category", "title", "description",
            "severity", "status",
            "detected_from_alert_id",
            "created_by", "assigned_to",
            "resolved_by", "closed_by",
            "due_at", "resolved_at", "closed_at", "cancelled_at",
            "resolution_note",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "created_by", "resolved_by", "closed_by",
            "resolved_at", "closed_at", "cancelled_at",
            "created_at", "updated_at",
        ]


class CentralIssueCreateSerializer(serializers.Serializer):
    """Input serializer for creating a new CentralIssue."""
    organization_id = serializers.UUIDField()
    restaurant_id = serializers.UUIDField(required=False, allow_null=True)
    branch_id = serializers.UUIDField(required=False, allow_null=True)
    category = serializers.ChoiceField(choices=ISSUE_CATEGORY_CHOICES)
    title = serializers.CharField(max_length=300)
    description = serializers.CharField()
    severity = serializers.ChoiceField(choices=ISSUE_SEVERITY_CHOICES)
    due_at = serializers.DateTimeField(required=False, allow_null=True)

    def validate(self, attrs):
        from organizations.models import Organization, Restaurant, Branch
        from accounts import access as acl

        request = self.context["request"]

        # Resolve and scope-check organization
        try:
            org = Organization.objects.get(pk=attrs["organization_id"])
        except Organization.DoesNotExist:
            raise serializers.ValidationError({"organization_id": "Not found."})
        if not acl.can_access_organization(request.user, org):
            raise serializers.ValidationError({"organization_id": "Access denied."})
        attrs["organization"] = org

        # Resolve and scope-check restaurant
        restaurant_id = attrs.pop("restaurant_id", None)
        attrs["restaurant"] = None
        if restaurant_id:
            try:
                r = Restaurant.objects.get(pk=restaurant_id, organization=org)
            except Restaurant.DoesNotExist:
                raise serializers.ValidationError({"restaurant_id": "Not found."})
            if not acl.can_access_restaurant(request.user, r):
                raise serializers.ValidationError({"restaurant_id": "Access denied."})
            attrs["restaurant"] = r

        # Resolve and scope-check branch
        branch_id = attrs.pop("branch_id", None)
        attrs["branch"] = None
        if branch_id:
            try:
                b = Branch.objects.get(pk=branch_id)
            except Branch.DoesNotExist:
                raise serializers.ValidationError({"branch_id": "Not found."})
            if not acl.can_access_branch(request.user, b):
                raise serializers.ValidationError({"branch_id": "Access denied."})
            attrs["branch"] = b

        attrs.pop("organization_id", None)
        return attrs


# ---------------------------------------------------------------------------
# CentralSystemEvent
# ---------------------------------------------------------------------------

class CentralSystemEventSerializer(serializers.ModelSerializer):
    organization = OrganizationMiniSerializer(read_only=True)
    restaurant = RestaurantMiniSerializer(read_only=True)
    branch = BranchMiniSerializer(read_only=True)
    alert_id = serializers.UUIDField(source="alert.pk", read_only=True, allow_null=True)
    issue_id = serializers.UUIDField(source="issue.pk", read_only=True, allow_null=True)

    class Meta:
        model = CentralSystemEvent
        fields = [
            "id", "organization", "restaurant", "branch",
            "event_type", "severity", "title", "description",
            "alert_id", "issue_id",
            "metadata", "occurred_at",
            "created_at",
        ]
        read_only_fields = fields


# ---------------------------------------------------------------------------
# CentralControlAuditLog
# ---------------------------------------------------------------------------

class CentralControlAuditLogSerializer(serializers.ModelSerializer):
    actor = UserMiniSerializer(read_only=True)
    organization = OrganizationMiniSerializer(read_only=True)

    class Meta:
        model = CentralControlAuditLog
        fields = [
            "id", "actor", "action",
            "entity_type", "entity_id",
            "organization",
            "old_status", "new_status",
            "metadata", "created_at",
        ]
        read_only_fields = fields


# ---------------------------------------------------------------------------
# Restaurant / Branch overview serializers
# ---------------------------------------------------------------------------

class RestaurantOverviewSerializer(serializers.Serializer):
    """Minimal restaurant overview for the Central Control restaurant list."""
    id = serializers.UUIDField()
    name = serializers.CharField()
    is_active = serializers.BooleanField()
    organization_id = serializers.UUIDField(source="organization.pk")
    organization_name = serializers.CharField(source="organization.name")
    branch_count = serializers.SerializerMethodField()
    active_branch_count = serializers.SerializerMethodField()

    def get_branch_count(self, obj):
        return obj.branches.count()

    def get_active_branch_count(self, obj):
        return obj.branches.filter(is_active=True).count()


class BranchOverviewSerializer(serializers.Serializer):
    """Minimal branch overview for the Central Control branch list."""
    id = serializers.UUIDField()
    name = serializers.CharField()
    is_active = serializers.BooleanField()
    restaurant_id = serializers.UUIDField(source="restaurant.pk")
    restaurant_name = serializers.CharField(source="restaurant.name")
    city = serializers.CharField()
    phone = serializers.CharField()


# ---------------------------------------------------------------------------
# User summary (safe — never exposes passwords/tokens)
# ---------------------------------------------------------------------------

class CentralUserSummarySerializer(serializers.Serializer):
    """Safe read-only user summary for Central Control user access monitoring."""
    id = serializers.IntegerField()
    email = serializers.EmailField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    is_active = serializers.BooleanField()
    date_joined = serializers.DateTimeField()
    last_login = serializers.DateTimeField(allow_null=True)
