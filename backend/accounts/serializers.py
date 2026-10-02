# =============================================================================
# RestaurantFlow — Accounts Serializers
# Phase 3: Users, Roles, Permissions, UserRoleAssignment
#
# Security rules enforced here:
#   - password / password_hash never appear in output.
#   - is_superuser / is_staff cannot be set via normal user-creation.
#   - Scope hierarchy validated in UserRoleAssignmentSerializer.validate().
#   - UserCreateSerializer delegates final creation to accounts.services.
# =============================================================================

import logging
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from accounts import access as acl
from .models import UserProfile, Role, Permission, UserRoleAssignment

logger = logging.getLogger("accounts")
User = get_user_model()


# =============================================================================
# UserProfile
# =============================================================================

class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = [
            "display_name",
            "employee_code",
            "profile_photo",
            "is_active",
        ]
        read_only_fields = []


# =============================================================================
# Permission
# =============================================================================

class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = [
            "id",
            "code",
            "name",
            "description",
            "module",
            "action",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


# =============================================================================
# Role
# =============================================================================

class RoleSerializer(serializers.ModelSerializer):
    permissions = PermissionSerializer(many=True, read_only=True)
    permission_codes = serializers.SerializerMethodField()

    class Meta:
        model = Role
        fields = [
            "id",
            "name",
            "code",
            "description",
            "scope",
            "is_system_role",
            "is_active",
            "permissions",
            "permission_codes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "is_system_role", "created_at", "updated_at"]

    def get_permission_codes(self, obj):
        return list(obj.permissions.filter(is_active=True).values_list("code", flat=True))


class RoleMinimalSerializer(serializers.ModelSerializer):
    """Lightweight role serializer for embedding inside user responses."""

    class Meta:
        model = Role
        fields = ["id", "name", "code", "scope"]


# =============================================================================
# UserRoleAssignment
# =============================================================================

class UserRoleAssignmentSerializer(serializers.ModelSerializer):
    role_detail = RoleMinimalSerializer(source="role", read_only=True)
    organization_name = serializers.SerializerMethodField()
    restaurant_name = serializers.SerializerMethodField()
    branch_name = serializers.SerializerMethodField()

    class Meta:
        model = UserRoleAssignment
        fields = [
            "id",
            "user",
            "role",
            "role_detail",
            "organization",
            "organization_name",
            "restaurant",
            "restaurant_name",
            "branch",
            "branch_name",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_organization_name(self, obj):
        return obj.organization.name if obj.organization else None

    def get_restaurant_name(self, obj):
        return obj.restaurant.name if obj.restaurant else None

    def get_branch_name(self, obj):
        return obj.branch.name if obj.branch else None

    def validate(self, attrs):
        """
        Validate scope hierarchy relationships.
        Branch must belong to restaurant; restaurant must belong to organization.
        Role scope must be respected.
        """
        role = attrs.get("role") or (self.instance.role if self.instance else None)
        organization = attrs.get("organization")
        restaurant = attrs.get("restaurant")
        branch = attrs.get("branch")

        if not role:
            raise serializers.ValidationError({"role": "Role is required."})

        # Hierarchy: restaurant → organization
        if restaurant and organization:
            if str(restaurant.organization_id) != str(organization.pk):
                raise serializers.ValidationError(
                    {"restaurant": "This restaurant does not belong to the selected organization."}
                )

        # Hierarchy: branch → restaurant
        if branch and restaurant:
            if str(branch.restaurant_id) != str(restaurant.pk):
                raise serializers.ValidationError(
                    {"branch": "This branch does not belong to the selected restaurant."}
                )

        if branch and not restaurant:
            raise serializers.ValidationError(
                {"restaurant": "A restaurant must be specified when assigning a branch."}
            )

        if restaurant and not organization:
            raise serializers.ValidationError(
                {"organization": "An organization must be specified when assigning a restaurant."}
            )

        # Role scope validation
        if role.scope == Role.SCOPE_ORGANIZATION:
            if restaurant or branch:
                raise serializers.ValidationError(
                    f"Role '{role.code}' has organization scope. Restaurant and branch must be empty."
                )
            if not organization:
                raise serializers.ValidationError(
                    {"organization": f"Role '{role.code}' requires an organization."}
                )
        elif role.scope == Role.SCOPE_RESTAURANT:
            if branch:
                raise serializers.ValidationError(
                    f"Role '{role.code}' has restaurant scope. Branch must be empty."
                )
            if not restaurant:
                raise serializers.ValidationError(
                    {"restaurant": f"Role '{role.code}' requires a restaurant."}
                )

        return attrs


class UserRoleAssignmentCreateSerializer(serializers.ModelSerializer):
    """Used when creating a new assignment. User is supplied in the URL."""

    class Meta:
        model = UserRoleAssignment
        fields = [
            "id",
            "role",
            "organization",
            "restaurant",
            "branch",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate(self, attrs):
        # Reuse scope validation from the full serializer
        role = attrs.get("role")
        organization = attrs.get("organization")
        restaurant = attrs.get("restaurant")
        branch = attrs.get("branch")

        if restaurant and organization:
            if str(restaurant.organization_id) != str(organization.pk):
                raise serializers.ValidationError(
                    {"restaurant": "This restaurant does not belong to the selected organization."}
                )

        if branch and restaurant:
            if str(branch.restaurant_id) != str(restaurant.pk):
                raise serializers.ValidationError(
                    {"branch": "This branch does not belong to the selected restaurant."}
                )

        if branch and not restaurant:
            raise serializers.ValidationError(
                {"restaurant": "A restaurant must be specified when assigning a branch."}
            )

        if restaurant and not organization:
            raise serializers.ValidationError(
                {"organization": "An organization must be specified when assigning a restaurant."}
            )

        if role:
            if role.scope == Role.SCOPE_ORGANIZATION:
                if restaurant or branch:
                    raise serializers.ValidationError(
                        f"Role '{role.code}' has organization scope. Restaurant and branch must be empty."
                    )
                if not organization:
                    raise serializers.ValidationError(
                        {"organization": f"Role '{role.code}' requires an organization."}
                    )
            elif role.scope == Role.SCOPE_RESTAURANT:
                if branch:
                    raise serializers.ValidationError(
                        f"Role '{role.code}' has restaurant scope. Branch must be empty."
                    )
                if not restaurant:
                    raise serializers.ValidationError(
                        {"restaurant": f"Role '{role.code}' requires a restaurant."}
                    )

        return attrs


# =============================================================================
# User — read-only serializer (for /api/auth/me/ and list/detail)
# =============================================================================

class UserSerializer(serializers.ModelSerializer):
    """Safe read serializer — never exposes password or sensitive flags."""

    full_name = serializers.ReadOnlyField()
    profile = UserProfileSerializer(read_only=True)
    scope = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "full_name",
            "phone",
            "is_active",
            "date_joined",
            "updated_at",
            "profile",
            "scope",
        ]
        read_only_fields = ["id", "date_joined", "updated_at"]

    def get_scope(self, obj):
        return acl.get_user_scope_summary(obj)


class UserMinimalSerializer(serializers.ModelSerializer):
    """Tiny serializer for embedding user info inside other objects."""

    full_name = serializers.ReadOnlyField()

    class Meta:
        model = User
        fields = ["id", "email", "full_name", "phone", "is_active"]


# =============================================================================
# User — detail with role assignments
# =============================================================================

class UserDetailSerializer(serializers.ModelSerializer):
    full_name = serializers.ReadOnlyField()
    profile = UserProfileSerializer(read_only=True)
    role_assignments = UserRoleAssignmentSerializer(many=True, read_only=True)
    permissions = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "full_name",
            "phone",
            "is_active",
            "is_staff",
            "date_joined",
            "last_login",
            "updated_at",
            "profile",
            "role_assignments",
            "permissions",
        ]
        read_only_fields = [
            "id",
            "is_staff",
            "date_joined",
            "last_login",
            "updated_at",
            "role_assignments",
            "permissions",
        ]

    def get_permissions(self, obj):
        return sorted(obj.get_permissions_set())


# =============================================================================
# User — update (PATCH)
# =============================================================================

class UserUpdateSerializer(serializers.ModelSerializer):
    """
    Allows updating safe fields only.
    is_superuser / is_staff are explicitly excluded.
    """

    profile = UserProfileSerializer(required=False)

    class Meta:
        model = User
        fields = [
            "first_name",
            "last_name",
            "phone",
            "profile",
        ]

    def update(self, instance, validated_data):
        profile_data = validated_data.pop("profile", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if profile_data is not None:
            profile, _ = UserProfile.objects.get_or_create(user=instance)
            for attr, value in profile_data.items():
                setattr(profile, attr, value)
            profile.save()

        return instance


# =============================================================================
# User — registration (public endpoint)
# =============================================================================

class RegisterSerializer(serializers.ModelSerializer):
    """Public registration serializer. Cannot set staff/superuser flags."""

    password = serializers.CharField(
        write_only=True, min_length=8, style={"input_type": "password"}
    )
    password_confirm = serializers.CharField(
        write_only=True, style={"input_type": "password"}
    )

    class Meta:
        model = User
        fields = [
            "email",
            "first_name",
            "last_name",
            "phone",
            "password",
            "password_confirm",
        ]

    def validate_password(self, value):
        validate_password(value)
        return value

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError({"password": "Passwords do not match."})
        return attrs

    def create(self, validated_data):
        validated_data.pop("password_confirm")
        user = User.objects.create_user(**validated_data)
        # Auto-create profile
        UserProfile.objects.get_or_create(user=user)
        return user


# =============================================================================
# User — admin creation (privileged endpoint)
# =============================================================================

class UserCreateSerializer(serializers.ModelSerializer):
    """
    Privileged user creation.  Used by org/restaurant admins to create staff.
    Never accepts is_superuser or is_staff from input.
    Password is hashed via create_user().
    """

    password = serializers.CharField(
        write_only=True, min_length=8, style={"input_type": "password"}
    )

    class Meta:
        model = User
        fields = [
            "email",
            "first_name",
            "last_name",
            "phone",
            "password",
        ]

    def validate_password(self, value):
        validate_password(value)
        return value

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value.lower()

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        UserProfile.objects.get_or_create(user=user)
        return user
