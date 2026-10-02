# =============================================================================
# RestaurantFlow — Accounts Admin
# Phase 3: User, UserProfile, Role, Permission, UserRoleAssignment
# =============================================================================

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from .models import User, UserProfile, Role, Permission, UserRoleAssignment


# =============================================================================
# Inlines
# =============================================================================

class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name = "Profile"
    fields = ["display_name", "employee_code", "profile_photo", "is_active"]
    readonly_fields = []


class UserRoleAssignmentInline(admin.TabularInline):
    model = UserRoleAssignment
    extra = 0
    fields = ["role", "organization", "restaurant", "branch", "is_active"]
    readonly_fields = ["created_at"]
    show_change_link = True
    verbose_name = "Role Assignment"
    verbose_name_plural = "Role Assignments"


# =============================================================================
# User admin
# =============================================================================

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = [
        "email",
        "full_name",
        "phone",
        "is_active",
        "is_staff",
        "date_joined",
    ]
    list_filter = ["is_active", "is_staff", "is_superuser"]
    search_fields = ["email", "first_name", "last_name", "phone"]
    ordering = ["-date_joined"]
    inlines = [UserProfileInline, UserRoleAssignmentInline]

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (_("Personal info"), {"fields": ("first_name", "last_name", "phone")}),
        (
            _("Permissions"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        (_("Important dates"), {"fields": ("last_login", "date_joined")}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "first_name",
                    "last_name",
                    "phone",
                    "password1",
                    "password2",
                ),
            },
        ),
    )

    def full_name(self, obj):
        return obj.full_name
    full_name.short_description = "Name"


# =============================================================================
# UserProfile admin
# =============================================================================

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ["user", "display_name", "employee_code", "is_active", "created_at"]
    list_filter = ["is_active"]
    search_fields = ["user__email", "display_name", "employee_code"]
    readonly_fields = ["id", "created_at", "updated_at"]
    raw_id_fields = ["user"]

    fieldsets = (
        (
            "Identity",
            {"fields": ("id", "user", "display_name", "employee_code", "profile_photo", "is_active")},
        ),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )


# =============================================================================
# Permission admin
# =============================================================================

@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "module", "action", "is_active", "created_at"]
    list_filter = ["module", "is_active"]
    search_fields = ["code", "name", "description"]
    ordering = ["module", "action"]
    readonly_fields = ["id", "created_at", "updated_at"]

    fieldsets = (
        (
            "Identity",
            {"fields": ("id", "code", "name", "description", "module", "action", "is_active")},
        ),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )


# =============================================================================
# Role admin
# =============================================================================

@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "code",
        "scope",
        "is_system_role",
        "is_active",
        "permission_count",
        "created_at",
    ]
    list_filter = ["scope", "is_system_role", "is_active"]
    search_fields = ["name", "code", "description"]
    ordering = ["name"]
    readonly_fields = ["id", "created_at", "updated_at"]
    filter_horizontal = ["permissions"]

    fieldsets = (
        (
            "Identity",
            {
                "fields": (
                    "id",
                    "name",
                    "code",
                    "description",
                    "scope",
                    "is_system_role",
                    "is_active",
                )
            },
        ),
        ("Permissions", {"fields": ("permissions",)}),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    def permission_count(self, obj):
        return obj.permissions.count()
    permission_count.short_description = "# Perms"

    def has_delete_permission(self, request, obj=None):
        # Prevent deletion of system roles; use is_active instead
        if obj and obj.is_system_role:
            return False
        return super().has_delete_permission(request, obj)


# =============================================================================
# UserRoleAssignment admin
# =============================================================================

@admin.register(UserRoleAssignment)
class UserRoleAssignmentAdmin(admin.ModelAdmin):
    list_display = [
        "user",
        "role",
        "organization",
        "restaurant",
        "branch",
        "is_active",
        "created_at",
    ]
    list_filter = ["is_active", "role__scope", "role"]
    search_fields = [
        "user__email",
        "role__name",
        "organization__name",
        "restaurant__name",
        "branch__name",
    ]
    ordering = ["-created_at"]
    readonly_fields = ["id", "created_at", "updated_at"]
    raw_id_fields = ["user", "organization", "restaurant", "branch"]

    fieldsets = (
        (
            "Assignment",
            {
                "fields": (
                    "id",
                    "user",
                    "role",
                    "is_active",
                )
            },
        ),
        (
            "Scope",
            {
                "fields": (
                    "organization",
                    "restaurant",
                    "branch",
                )
            },
        ),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )
