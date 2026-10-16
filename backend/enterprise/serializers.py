# =============================================================================
# RestaurantFlow — Enterprise Serializers
# Phase 20
#
# Convention:
#   Read serializers  — ModelSerializer with nested/computed fields, all read_only.
#   Write serializers — plain Serializer for validated input only.
#
# Rules:
#   - Never accept financial totals or computed values from the client.
#   - Never trust company/restaurant/branch IDs from the payload.
#     Resolve them in the view from the authenticated user's scope.
#   - Monetary fields always returned as string with 2dp.
#   - UUIDs always returned as strings.
# =============================================================================

from decimal import Decimal
from rest_framework import serializers

from enterprise.constants import (
    ALLOWED_CONFIGURATION_KEY_CHOICES,
    VALUE_TYPE_CHOICES,
    CONFIG_SCOPE_CHOICES,
    ROLLOUT_TYPE_CHOICES,
    ROLLOUT_SCOPE_CHOICES,
    ROLLOUT_STATUS_CHOICES,
    TRANSFER_STATUS_CHOICES,
    POLICY_TYPE_CHOICES,
    CLOSURE_TYPE_CHOICES,
    CLOSURE_STATUS_CHOICES,
    BRANCH_STATUS_CHOICES,
    DAY_OF_WEEK_CHOICES,
    AUDIT_ACTION_CHOICES,
)
from enterprise.models import (
    BranchOperationalStatus,
    BranchOperatingHour,
    BranchClosure,
    EnterpriseConfiguration,
    ConfigurationChange,
    MenuRollout,
    MenuRolloutBranch,
    StaffBranchAssignment,
    StaffTransfer,
    ApprovalPolicy,
    EnterpriseAuditLog,
)


# =============================================================================
# Shared nested read serializers
# =============================================================================

class UserBriefSerializer(serializers.Serializer):
    """Minimal user representation for nested reads."""
    id    = serializers.IntegerField(read_only=True)
    email = serializers.EmailField(read_only=True)
    full_name = serializers.CharField(read_only=True)


class BranchBriefSerializer(serializers.Serializer):
    """Minimal branch representation."""
    id   = serializers.UUIDField(read_only=True)
    name = serializers.CharField(read_only=True)
    code = serializers.CharField(read_only=True)


class RestaurantBriefSerializer(serializers.Serializer):
    """Minimal restaurant representation."""
    id   = serializers.UUIDField(read_only=True)
    name = serializers.CharField(read_only=True)
    code = serializers.CharField(read_only=True)


class MenuItemBriefSerializer(serializers.Serializer):
    """Minimal menu item representation."""
    id   = serializers.UUIDField(read_only=True)
    name = serializers.CharField(read_only=True)
    sku  = serializers.CharField(read_only=True)


# =============================================================================
# BranchOperationalStatus
# =============================================================================

class BranchOperationalStatusSerializer(serializers.ModelSerializer):
    branch            = BranchBriefSerializer(read_only=True)
    status_changed_by = UserBriefSerializer(read_only=True)

    class Meta:
        model = BranchOperationalStatus
        fields = [
            "id", "branch", "status",
            "status_changed_at", "status_changed_by", "status_reason",
            "created_at", "updated_at",
        ]
        read_only_fields = fields


class SetBranchStatusSerializer(serializers.Serializer):
    """Write serializer for branch status transitions."""
    new_status = serializers.ChoiceField(choices=BRANCH_STATUS_CHOICES)
    reason     = serializers.CharField(max_length=500, required=False, default="")
    force      = serializers.BooleanField(default=False)


# =============================================================================
# BranchOperatingHour
# =============================================================================

class BranchOperatingHourSerializer(serializers.ModelSerializer):
    branch     = BranchBriefSerializer(read_only=True)
    is_overnight = serializers.SerializerMethodField()

    class Meta:
        model = BranchOperatingHour
        fields = [
            "id", "branch", "day_of_week",
            "opening_time", "closing_time", "is_closed",
            "is_overnight", "created_at", "updated_at",
        ]
        read_only_fields = fields

    def get_is_overnight(self, obj) -> bool:
        return obj.is_overnight


class UpsertOperatingHourSerializer(serializers.Serializer):
    """Write serializer for creating/updating a single operating hour."""
    day_of_week   = serializers.ChoiceField(choices=DAY_OF_WEEK_CHOICES)
    opening_time  = serializers.TimeField(required=False, allow_null=True)
    closing_time  = serializers.TimeField(required=False, allow_null=True)
    is_closed     = serializers.BooleanField(default=False)

    def validate(self, data):
        if not data.get("is_closed"):
            if not data.get("opening_time"):
                raise serializers.ValidationError(
                    {"opening_time": "Opening time is required when is_closed=False."}
                )
            if not data.get("closing_time"):
                raise serializers.ValidationError(
                    {"closing_time": "Closing time is required when is_closed=False."}
                )
        return data


class BulkUpsertOperatingHoursSerializer(serializers.Serializer):
    """Write serializer for bulk weekly schedule upsert."""
    hours = UpsertOperatingHourSerializer(many=True)

    def validate_hours(self, value):
        days_seen = set()
        for entry in value:
            day = entry.get("day_of_week")
            if day in days_seen:
                raise serializers.ValidationError(
                    f"Duplicate day_of_week '{day}' in request."
                )
            days_seen.add(day)
        return value


# =============================================================================
# BranchClosure
# =============================================================================

class BranchClosureSerializer(serializers.ModelSerializer):
    branch       = BranchBriefSerializer(read_only=True)
    created_by   = UserBriefSerializer(read_only=True)
    approved_by  = UserBriefSerializer(read_only=True)

    class Meta:
        model = BranchClosure
        fields = [
            "id", "branch", "closure_type",
            "start_datetime", "end_datetime", "reason",
            "status", "created_by", "approved_by",
            "approved_at", "rejected_at", "rejection_reason",
            "created_at", "updated_at",
        ]
        read_only_fields = fields


class CreateBranchClosureSerializer(serializers.Serializer):
    closure_type    = serializers.ChoiceField(choices=CLOSURE_TYPE_CHOICES)
    start_datetime  = serializers.DateTimeField()
    end_datetime    = serializers.DateTimeField()
    reason          = serializers.CharField(max_length=1000)
    auto_approve    = serializers.BooleanField(default=False)

    def validate(self, data):
        if data["end_datetime"] <= data["start_datetime"]:
            raise serializers.ValidationError(
                {"end_datetime": "End datetime must be after start datetime."}
            )
        return data


class RejectClosureSerializer(serializers.Serializer):
    rejection_reason = serializers.CharField(max_length=500, required=False, default="")


# =============================================================================
# EnterpriseConfiguration
# =============================================================================

class EnterpriseConfigurationSerializer(serializers.ModelSerializer):
    created_by = UserBriefSerializer(read_only=True)
    updated_by = UserBriefSerializer(read_only=True)
    scope      = serializers.CharField(read_only=True)

    class Meta:
        model = EnterpriseConfiguration
        fields = [
            "id", "company", "restaurant", "branch",
            "configuration_key", "configuration_value", "value_type",
            "scope", "is_active", "version",
            "created_by", "updated_by",
            "created_at", "updated_at",
        ]
        read_only_fields = fields


class SetConfigurationSerializer(serializers.Serializer):
    """Write serializer for creating / updating a configuration entry."""
    configuration_key   = serializers.ChoiceField(choices=ALLOWED_CONFIGURATION_KEY_CHOICES)
    configuration_value = serializers.CharField(max_length=2000)
    reason              = serializers.CharField(max_length=500, required=False, default="")
    # Scope is resolved server-side from URL params — not accepted from the client.


class BulkSetConfigurationSerializer(serializers.Serializer):
    """Write serializer for bulk configuration update."""

    class _Entry(serializers.Serializer):
        key   = serializers.ChoiceField(choices=ALLOWED_CONFIGURATION_KEY_CHOICES)
        value = serializers.CharField(max_length=2000)

    configs = _Entry(many=True)
    reason  = serializers.CharField(max_length=500, required=False, default="")


class RollbackConfigurationSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=500, required=False, default="")


class EffectiveConfigurationSerializer(serializers.Serializer):
    """Read-only representation of an effective configuration value with source."""
    key          = serializers.CharField(read_only=True)
    value        = serializers.SerializerMethodField()
    raw_value    = serializers.CharField(read_only=True)
    source       = serializers.CharField(read_only=True)
    is_overridden = serializers.BooleanField(read_only=True)
    description  = serializers.CharField(read_only=True)
    value_type   = serializers.CharField(read_only=True)

    def get_value(self, obj):
        # Ensure Decimal is serialized as string for frontend safety
        v = obj.get("value")
        if isinstance(v, Decimal):
            return str(v)
        return v


# =============================================================================
# ConfigurationChange
# =============================================================================

class ConfigurationChangeSerializer(serializers.ModelSerializer):
    changed_by = UserBriefSerializer(read_only=True)
    scope      = serializers.CharField(read_only=True)

    class Meta:
        model = ConfigurationChange
        fields = [
            "id", "company", "restaurant", "branch",
            "configuration_key", "old_value", "new_value",
            "version", "changed_by", "change_reason", "scope",
            "created_at",
        ]
        read_only_fields = fields


# =============================================================================
# MenuRollout
# =============================================================================

class MenuRolloutBranchSerializer(serializers.ModelSerializer):
    branch = BranchBriefSerializer(read_only=True)

    class Meta:
        model = MenuRolloutBranch
        fields = [
            "id", "branch", "result",
            "old_value", "new_value", "failure_reason",
            "created_at",
        ]
        read_only_fields = fields


class MenuRolloutSerializer(serializers.ModelSerializer):
    menu_item    = MenuItemBriefSerializer(read_only=True)
    restaurant   = RestaurantBriefSerializer(read_only=True)
    created_by   = UserBriefSerializer(read_only=True)
    approved_by  = UserBriefSerializer(read_only=True)
    source_branch = BranchBriefSerializer(read_only=True)
    branch_results = MenuRolloutBranchSerializer(many=True, read_only=True)

    class Meta:
        model = MenuRollout
        fields = [
            "id", "restaurant", "menu_item", "rollout_type",
            "new_price", "is_available", "force_override",
            "source_branch", "target_scope",
            "effective_from", "status",
            "created_by", "approved_by", "approved_at", "completed_at",
            "notes", "branch_results",
            "created_at", "updated_at",
        ]
        read_only_fields = fields


class CreateMenuRolloutSerializer(serializers.Serializer):
    menu_item_id       = serializers.UUIDField()
    rollout_type       = serializers.ChoiceField(choices=ROLLOUT_TYPE_CHOICES)
    target_scope       = serializers.ChoiceField(choices=ROLLOUT_SCOPE_CHOICES)
    target_branch_ids  = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        allow_empty=True,
        default=list,
    )
    is_available       = serializers.BooleanField(required=False, allow_null=True)
    new_price          = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False, allow_null=True
    )
    force_override     = serializers.BooleanField(default=False)
    effective_from     = serializers.DateTimeField(required=False, allow_null=True)
    notes              = serializers.CharField(max_length=1000, required=False, default="")

    def validate(self, data):
        from enterprise.constants import ROLLOUT_TYPE_PRICE, ROLLOUT_TYPE_MENU_AVAILABILITY
        rtype = data.get("rollout_type")
        if rtype == ROLLOUT_TYPE_PRICE and data.get("new_price") is None:
            raise serializers.ValidationError(
                {"new_price": "new_price is required for PRICE rollouts."}
            )
        if rtype == ROLLOUT_TYPE_MENU_AVAILABILITY and data.get("is_available") is None:
            raise serializers.ValidationError(
                {"is_available": "is_available is required for MENU_AVAILABILITY rollouts."}
            )
        return data


# =============================================================================
# StaffBranchAssignment
# =============================================================================

class StaffBranchAssignmentSerializer(serializers.ModelSerializer):
    user        = UserBriefSerializer(read_only=True)
    branch      = BranchBriefSerializer(read_only=True)
    restaurant  = RestaurantBriefSerializer(read_only=True)
    assigned_by = UserBriefSerializer(read_only=True)
    role_code   = serializers.SerializerMethodField()
    role_name   = serializers.SerializerMethodField()

    class Meta:
        model = StaffBranchAssignment
        fields = [
            "id", "user", "restaurant", "branch",
            "role_code", "role_name",
            "assigned_by", "assigned_at",
            "start_date", "end_date",
            "is_primary", "is_active",
            "created_at", "updated_at",
        ]
        read_only_fields = fields

    def get_role_code(self, obj) -> str:
        return obj.role.code if obj.role_id else None

    def get_role_name(self, obj) -> str:
        return obj.role.name if obj.role_id else None


class AssignStaffSerializer(serializers.Serializer):
    user_id     = serializers.IntegerField()
    role_id     = serializers.UUIDField()
    is_primary  = serializers.BooleanField(default=True)
    start_date  = serializers.DateField(required=False, allow_null=True)
    end_date    = serializers.DateField(required=False, allow_null=True)

    def validate(self, data):
        if data.get("end_date") and data.get("start_date"):
            if data["end_date"] < data["start_date"]:
                raise serializers.ValidationError(
                    {"end_date": "End date must be on or after start date."}
                )
        return data


# =============================================================================
# StaffTransfer
# =============================================================================

class StaffTransferSerializer(serializers.ModelSerializer):
    user               = UserBriefSerializer(read_only=True)
    restaurant         = RestaurantBriefSerializer(read_only=True)
    source_branch      = BranchBriefSerializer(read_only=True)
    destination_branch = BranchBriefSerializer(read_only=True)
    requested_by       = UserBriefSerializer(read_only=True)
    approved_by        = UserBriefSerializer(read_only=True)

    class Meta:
        model = StaffTransfer
        fields = [
            "id", "user", "restaurant",
            "source_branch", "destination_branch",
            "requested_by", "approved_by",
            "reason", "status",
            "requested_at", "approved_at", "completed_at",
            "rejected_at", "rejection_reason",
            "created_at", "updated_at",
        ]
        read_only_fields = fields


class RequestTransferSerializer(serializers.Serializer):
    user_id                = serializers.IntegerField()
    destination_branch_id  = serializers.UUIDField()
    reason                 = serializers.CharField(max_length=1000)


class RejectTransferSerializer(serializers.Serializer):
    rejection_reason = serializers.CharField(max_length=500, required=False, default="")


# =============================================================================
# ApprovalPolicy
# =============================================================================

class ApprovalPolicySerializer(serializers.ModelSerializer):
    restaurant   = RestaurantBriefSerializer(read_only=True)
    branch       = BranchBriefSerializer(read_only=True)
    required_role_code = serializers.SerializerMethodField()
    created_by   = UserBriefSerializer(read_only=True)
    updated_by   = UserBriefSerializer(read_only=True)

    class Meta:
        model = ApprovalPolicy
        fields = [
            "id", "company", "restaurant", "branch",
            "policy_type",
            "threshold_amount", "threshold_percentage",
            "required_permission", "required_role_code",
            "is_active",
            "created_by", "updated_by",
            "created_at", "updated_at",
        ]
        read_only_fields = fields

    def get_required_role_code(self, obj) -> str:
        return obj.required_role.code if obj.required_role_id else None


class CreateApprovalPolicySerializer(serializers.Serializer):
    policy_type           = serializers.ChoiceField(choices=POLICY_TYPE_CHOICES)
    required_permission   = serializers.CharField(max_length=100)
    threshold_amount      = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False, allow_null=True
    )
    threshold_percentage  = serializers.DecimalField(
        max_digits=5, decimal_places=2, required=False, allow_null=True
    )
    required_role_id      = serializers.UUIDField(required=False, allow_null=True)
    # Scope is resolved from URL params — not accepted from client payload


class UpdateApprovalPolicySerializer(serializers.Serializer):
    threshold_amount      = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False, allow_null=True
    )
    threshold_percentage  = serializers.DecimalField(
        max_digits=5, decimal_places=2, required=False, allow_null=True
    )
    required_permission   = serializers.CharField(max_length=100, required=False)
    required_role_id      = serializers.UUIDField(required=False, allow_null=True)
    is_active             = serializers.BooleanField(required=False)


# =============================================================================
# EnterpriseAuditLog
# =============================================================================

class EnterpriseAuditLogSerializer(serializers.ModelSerializer):
    performed_by = UserBriefSerializer(read_only=True)
    restaurant   = RestaurantBriefSerializer(read_only=True)
    branch       = BranchBriefSerializer(read_only=True)

    class Meta:
        model = EnterpriseAuditLog
        fields = [
            "id", "performed_by",
            "company", "restaurant", "branch",
            "action", "description",
            "source_type", "source_id",
            "metadata", "created_at",
        ]
        read_only_fields = fields


# =============================================================================
# Dashboard
# =============================================================================

class EnterpriseDashboardSerializer(serializers.Serializer):
    """Read-only serializer for the enterprise dashboard summary."""
    total_restaurants      = serializers.IntegerField(read_only=True)
    total_branches         = serializers.IntegerField(read_only=True)
    active_branches        = serializers.IntegerField(read_only=True)
    temporarily_closed     = serializers.IntegerField(read_only=True)
    scheduled_closures     = serializers.IntegerField(read_only=True)
    pending_transfers      = serializers.IntegerField(read_only=True)
    pending_rollouts       = serializers.IntegerField(read_only=True)
    pending_closures       = serializers.IntegerField(read_only=True)
    failed_rollouts_24h    = serializers.IntegerField(read_only=True)


# =============================================================================
# Opening checklist
# =============================================================================

class ChecklistItemSerializer(serializers.Serializer):
    type   = serializers.CharField(read_only=True)
    label  = serializers.CharField(read_only=True)
    status = serializers.CharField(read_only=True)
    detail = serializers.CharField(read_only=True)


# =============================================================================
# Rollout preview
# =============================================================================

class RolloutPreviewBranchSerializer(serializers.Serializer):
    branch_id     = serializers.UUIDField(read_only=True)
    branch_name   = serializers.CharField(read_only=True)
    branch_code   = serializers.CharField(read_only=True)
    current_value = serializers.CharField(read_only=True, allow_null=True)
    new_value     = serializers.CharField(read_only=True, allow_null=True)
    will_change   = serializers.BooleanField(read_only=True)
    skip_reason   = serializers.CharField(read_only=True, allow_null=True)


class RolloutPreviewSerializer(serializers.Serializer):
    rollout_id          = serializers.UUIDField(read_only=True)
    rollout_type        = serializers.CharField(read_only=True)
    menu_item           = MenuItemBriefSerializer(read_only=True)
    target_scope        = serializers.CharField(read_only=True)
    force_override      = serializers.BooleanField(read_only=True)
    total_branches      = serializers.IntegerField(read_only=True)
    will_change_count   = serializers.IntegerField(read_only=True)
    will_skip_count     = serializers.IntegerField(read_only=True)
    branches            = RolloutPreviewBranchSerializer(many=True, read_only=True)


# =============================================================================
# Approval policy resolution (for frontend display)
# =============================================================================

class PolicyResolutionSerializer(serializers.Serializer):
    requires_approval    = serializers.BooleanField(read_only=True)
    policy_found         = serializers.BooleanField(read_only=True)
    policy_scope         = serializers.CharField(read_only=True, allow_null=True)
    required_permission  = serializers.CharField(read_only=True, allow_null=True)
    required_role        = serializers.CharField(read_only=True, allow_null=True)
    threshold_amount     = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True, allow_null=True
    )
    threshold_percentage = serializers.DecimalField(
        max_digits=5, decimal_places=2, read_only=True, allow_null=True
    )
