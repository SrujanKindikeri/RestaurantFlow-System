# =============================================================================
# RestaurantFlow — Notifications Serializers
# Phase 16
# =============================================================================

from rest_framework import serializers

from notifications.models import (
    Notification,
    NotificationRecipient,
    NotificationDelivery,
    NotificationPreference,
    NotificationTemplate,
    NotificationProviderConfig,
)
from notifications.constants import (
    NOTIFICATION_TYPE_CHOICES,
    CHANNEL_CHOICES,
    SEVERITY_CHOICES,
    DELIVERY_STATUS_CHOICES,
    RECIPIENT_STATUS_CHOICES,
)


# ---------------------------------------------------------------------------
# Notification
# ---------------------------------------------------------------------------

class NotificationSerializer(serializers.ModelSerializer):
    """
    Read-only representation of a Notification.
    Used inside NotificationRecipientSerializer.
    """

    class Meta:
        model  = Notification
        fields = [
            "id", "notification_type", "severity",
            "title", "message",
            "source_type", "source_id",
            "action_url", "metadata",
            "created_at", "expires_at",
        ]
        read_only_fields = fields


# ---------------------------------------------------------------------------
# NotificationRecipient — what the frontend list view returns
# ---------------------------------------------------------------------------

class NotificationRecipientSerializer(serializers.ModelSerializer):
    """
    Per-user notification with read state embedded.
    This is the primary shape returned by GET /api/notifications/.
    """

    notification = NotificationSerializer(read_only=True)
    is_read      = serializers.BooleanField(read_only=True)

    class Meta:
        model  = NotificationRecipient
        fields = [
            "id",
            "notification",
            "delivery_status",
            "read_at",
            "acknowledged_at",
            "delivered_at",
            "is_read",
            "created_at",
        ]
        read_only_fields = fields


# ---------------------------------------------------------------------------
# NotificationDelivery — admin delivery history
# ---------------------------------------------------------------------------

class NotificationDeliverySerializer(serializers.ModelSerializer):
    user_email = serializers.SerializerMethodField()

    class Meta:
        model  = NotificationDelivery
        fields = [
            "id", "notification", "recipient",
            "channel", "provider", "status",
            "attempt_count", "provider_message_id",
            "queued_at", "sent_at", "failed_at",
            "failure_reason", "next_retry_at",
            "user_email",
            "created_at", "updated_at",
        ]
        read_only_fields = fields

    def get_user_email(self, obj) -> str:
        try:
            return obj.recipient.user.email
        except Exception:
            return ""


# ---------------------------------------------------------------------------
# NotificationPreference
# ---------------------------------------------------------------------------

class NotificationPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model  = NotificationPreference
        fields = ["id", "notification_type", "channel", "enabled", "updated_at"]
        read_only_fields = ["id", "updated_at"]


class NotificationPreferenceUpdateSerializer(serializers.Serializer):
    """Used for PATCH /api/notifications/preferences/{id}/"""
    enabled = serializers.BooleanField()


class NotificationPreferenceBulkSerializer(serializers.Serializer):
    """Used for POST /api/notifications/preferences/ (bulk upsert)."""
    notification_type = serializers.ChoiceField(choices=NOTIFICATION_TYPE_CHOICES)
    channel           = serializers.ChoiceField(choices=CHANNEL_CHOICES)
    enabled           = serializers.BooleanField()


# ---------------------------------------------------------------------------
# NotificationTemplate
# ---------------------------------------------------------------------------

class NotificationTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model  = NotificationTemplate
        fields = [
            "id", "company", "notification_type", "channel",
            "subject_template", "body_template", "is_active",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_body_template(self, value):
        from notifications.validators import validate_template_variables
        validate_template_variables(value)
        return value

    def validate_subject_template(self, value):
        if value:
            from notifications.validators import validate_template_variables
            validate_template_variables(value)
        return value


# ---------------------------------------------------------------------------
# NotificationProviderConfig — admin only (no secrets exposed)
# ---------------------------------------------------------------------------

class NotificationProviderConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model  = NotificationProviderConfig
        fields = [
            "id", "company", "channel", "provider",
            "is_enabled", "configuration_metadata",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "company", "created_at", "updated_at"]

    def validate_configuration_metadata(self, value):
        """Prevent secrets from being stored in configuration_metadata."""
        forbidden_keys = {
            "api_key", "api_secret", "password", "token", "secret",
            "access_token", "auth_token", "private_key",
        }
        if isinstance(value, dict):
            for key in value:
                if key.lower() in forbidden_keys:
                    raise serializers.ValidationError(
                        f"Key '{key}' must not be stored in configuration_metadata. "
                        "Store secrets in environment variables."
                    )
        return value


# ---------------------------------------------------------------------------
# Unread count response
# ---------------------------------------------------------------------------

class UnreadCountSerializer(serializers.Serializer):
    count = serializers.IntegerField()
