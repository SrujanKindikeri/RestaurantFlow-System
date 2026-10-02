# =============================================================================
# RestaurantFlow — Accounts Serializers
# Phase 1 Foundation
# =============================================================================

import logging
from django.contrib.auth import get_user_model
from rest_framework import serializers

logger = logging.getLogger("accounts")
User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """Read-only serializer for returning user data safely."""

    full_name = serializers.ReadOnlyField()

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "full_name",
            "is_active",
            "date_joined",
        ]
        read_only_fields = ["id", "date_joined"]


class RegisterSerializer(serializers.ModelSerializer):
    """Serializer for user registration."""

    password = serializers.CharField(write_only=True, min_length=8, style={"input_type": "password"})
    password_confirm = serializers.CharField(write_only=True, style={"input_type": "password"})

    class Meta:
        model = User
        fields = [
            "email",
            "first_name",
            "last_name",
            "password",
            "password_confirm",
        ]

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError({"password": "Passwords do not match."})
        return attrs

    def create(self, validated_data):
        validated_data.pop("password_confirm")
        user = User.objects.create_user(**validated_data)
        return user
