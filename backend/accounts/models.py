# =============================================================================
# RestaurantFlow — Accounts Models
# Phase 3: Users, Roles, Permissions, UserProfile, UserRoleAssignment
#
# Model hierarchy:
#   User  (custom auth model — email-based, UUID-keyed via PermissionsMixin)
#   UserProfile  (extended profile — employee code, display name, photo)
#   Role  (system roles: COMPANY_HEAD, RESTAURANT_OWNER, etc.)
#   Permission  (granular permission codes: restaurant.view, bill.create, etc.)
#   UserRoleAssignment  (scoped assignment: user → role → org → restaurant → branch)
#
# Security principles:
#   - UUID primary keys on all business models.
#   - Soft disable via is_active — never hard-delete.
#   - Scope validation enforced at DB constraint level and in serializer.
#   - Role-Permission is M2M — flexible, not hard-coded checks.
#   - Employee codes are unique within org scope, not used as PKs.
# =============================================================================

import uuid
import logging
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.db import models
from django.utils import timezone

from core.models import TimestampedModel

logger = logging.getLogger("accounts")


# =============================================================================
# User Manager
# =============================================================================

class UserManager(BaseUserManager):
    """Custom manager for the User model using email as the unique identifier."""

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email field is required.")
        email = self.normalize_email(email)
        extra_fields.setdefault("is_active", True)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        logger.info("User created: %s", email)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(email, password, **extra_fields)


# =============================================================================
# User
# =============================================================================

class User(AbstractBaseUser, PermissionsMixin):
    """
    Custom User model for RestaurantFlow.

    Uses email as the primary identifier.
    Django's default BigAutoField id is kept intentionally — UUID scope is
    handled via UserRoleAssignment.  This avoids a costly AUTH_USER_MODEL
    migration on an already-seeded project.

    Phase 3 additions:
        - phone
        - profile (reverse OneToOne to UserProfile)
        - role_assignments (reverse M2M to UserRoleAssignment)
    """

    # -------------------------------------------------------------------------
    # Core identity
    # -------------------------------------------------------------------------
    email = models.EmailField(unique=True, db_index=True)
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    phone = models.CharField(max_length=30, blank=True, db_index=True)

    # -------------------------------------------------------------------------
    # Status flags
    # -------------------------------------------------------------------------
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    # -------------------------------------------------------------------------
    # Timestamps
    # -------------------------------------------------------------------------
    date_joined = models.DateTimeField(default=timezone.now)
    last_login = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"
        ordering = ["-date_joined"]
        indexes = [
            models.Index(fields=["email"]),
            models.Index(fields=["is_active"]),
        ]

    def __str__(self):
        return self.email

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip() or self.email

    # ------------------------------------------------------------------
    # Convenience helpers used by access-control layer
    # ------------------------------------------------------------------

    def get_active_assignments(self):
        """Return all active UserRoleAssignments for this user."""
        return self.role_assignments.filter(is_active=True).select_related(
            "role", "organization", "restaurant", "branch"
        )

    def get_permissions_set(self):
        """
        Return a flat set of all permission codes granted to this user
        across all their active role assignments.
        """
        if self.is_superuser:
            # Superuser bypasses all permission checks.
            # Late import avoids any potential forward-reference issues at module load.
            return set(Permission.objects.values_list("code", flat=True))

        codes = set()
        for assignment in self.get_active_assignments():
            if assignment.role.is_active:
                codes.update(
                    assignment.role.permissions.filter(is_active=True).values_list(
                        "code", flat=True
                    )
                )
        return codes

    def has_perm_code(self, code: str) -> bool:
        """Check if this user has a specific permission code."""
        if not self.is_active:
            return False
        if self.is_superuser:
            return True
        return code in self.get_permissions_set()


# =============================================================================
# UserProfile
# =============================================================================

class UserProfile(TimestampedModel):
    """
    Extended profile for operational staff.

    Kept separate from User to avoid bloating the auth model.
    One-to-one with User; created automatically via signal or explicit save.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    display_name = models.CharField(max_length=150, blank=True)
    employee_code = models.CharField(max_length=50, blank=True, db_index=True)
    profile_photo = models.ImageField(
        upload_to="profile_photos/",
        null=True,
        blank=True,
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"

    def __str__(self):
        return f"Profile — {self.user.email}"

    @property
    def effective_display_name(self):
        return self.display_name or self.user.full_name


# =============================================================================
# Permission
# =============================================================================

class Permission(TimestampedModel):
    """
    Granular permission code.

    Permissions are registered centrally and assigned to Roles.
    They are never checked by hard-coded role names — always by code.

    Examples:
        restaurant.view
        branch.create
        order.create
        bill.print
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=100, unique=True, db_index=True)
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    module = models.CharField(max_length=50, db_index=True)   # e.g. "restaurant", "order"
    action = models.CharField(max_length=50, db_index=True)   # e.g. "view", "create"
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        verbose_name = "Permission"
        verbose_name_plural = "Permissions"
        ordering = ["module", "action"]
        indexes = [
            models.Index(fields=["module", "action"]),
            models.Index(fields=["is_active"]),
        ]

    def __str__(self):
        return self.code


# =============================================================================
# Role
# =============================================================================

class Role(TimestampedModel):
    """
    A named role that can be assigned to users.

    System roles (is_system_role=True) are seeded by the seed command and
    should not be deleted — use is_active=False to disable them.

    The `scope` field documents the intended scope of the role:
        organization  — Company Head, Central Admin
        restaurant    — Restaurant Owner
        branch        — Manager, Cashier, Waiter, Kitchen, Inventory, Accountant
    """

    SCOPE_ORGANIZATION = "organization"
    SCOPE_RESTAURANT = "restaurant"
    SCOPE_BRANCH = "branch"

    SCOPE_CHOICES = [
        (SCOPE_ORGANIZATION, "Organization"),
        (SCOPE_RESTAURANT, "Restaurant"),
        (SCOPE_BRANCH, "Branch"),
    ]

    # System role codes — used by the seed command and access-control layer
    CODE_COMPANY_HEAD = "COMPANY_HEAD"
    CODE_CENTRAL_ADMIN = "CENTRAL_ADMIN"
    CODE_RESTAURANT_OWNER = "RESTAURANT_OWNER"
    CODE_RESTAURANT_MANAGER = "RESTAURANT_MANAGER"
    CODE_CASHIER = "CASHIER"
    CODE_WAITER = "WAITER"
    CODE_KITCHEN_STAFF = "KITCHEN_STAFF"
    CODE_INVENTORY_STAFF = "INVENTORY_STAFF"
    CODE_ACCOUNTANT = "ACCOUNTANT"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=50, unique=True, db_index=True)
    description = models.TextField(blank=True)
    scope = models.CharField(
        max_length=20,
        choices=SCOPE_CHOICES,
        default=SCOPE_BRANCH,
        db_index=True,
    )
    is_system_role = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True, db_index=True)
    permissions = models.ManyToManyField(
        Permission,
        blank=True,
        related_name="roles",
    )

    class Meta:
        verbose_name = "Role"
        verbose_name_plural = "Roles"
        ordering = ["name"]
        indexes = [
            models.Index(fields=["code"]),
            models.Index(fields=["scope"]),
            models.Index(fields=["is_active"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.code})"


# =============================================================================
# UserRoleAssignment
# =============================================================================

class UserRoleAssignment(TimestampedModel):
    """
    Scoped assignment of a Role to a User within a specific resource scope.

    Examples:
        Company Head:
            user=Srujan, role=COMPANY_HEAD, org=RestaurantFlow Foods,
            restaurant=NULL, branch=NULL

        Restaurant Owner:
            user=OwnerA, role=RESTAURANT_OWNER, org=RestaurantFlow Foods,
            restaurant=Spice Garden, branch=NULL

        Branch Manager:
            user=ManagerA, role=RESTAURANT_MANAGER, org=RestaurantFlow Foods,
            restaurant=Spice Garden, branch=LPU Campus

    Scope validation (enforced in the serializer and service layer):
        - organization scope roles: restaurant=NULL, branch=NULL
        - restaurant scope roles:   restaurant required, branch=NULL
        - branch scope roles:       restaurant required, branch may be required

    DB-level guarantees:
        - branch.restaurant must equal restaurant (enforced in clean/save).
        - restaurant.organization must equal organization (enforced in clean/save).
        - No orphaned assignments (PROTECT on all FKs).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="role_assignments",
    )
    role = models.ForeignKey(
        Role,
        on_delete=models.PROTECT,
        related_name="assignments",
    )

    # Scope fields — all nullable; actual requirements depend on role.scope
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="user_assignments",
    )
    restaurant = models.ForeignKey(
        "organizations.Restaurant",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="user_assignments",
    )
    branch = models.ForeignKey(
        "organizations.Branch",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="user_assignments",
    )

    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        verbose_name = "User Role Assignment"
        verbose_name_plural = "User Role Assignments"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "is_active"]),
            models.Index(fields=["role", "is_active"]),
            models.Index(fields=["organization", "is_active"]),
            models.Index(fields=["restaurant", "is_active"]),
            models.Index(fields=["branch", "is_active"]),
        ]

    def __str__(self):
        scope_parts = []
        if self.organization:
            scope_parts.append(self.organization.name)
        if self.restaurant:
            scope_parts.append(self.restaurant.name)
        if self.branch:
            scope_parts.append(self.branch.name)
        scope_str = " → ".join(scope_parts) if scope_parts else "global"
        return f"{self.user.email} | {self.role.code} | {scope_str}"

    def clean(self):
        """Validate scope hierarchy consistency."""
        from django.core.exceptions import ValidationError

        # Branch must belong to the specified restaurant
        if self.branch and self.restaurant:
            if self.branch.restaurant_id != self.restaurant.pk:
                raise ValidationError(
                    "The selected branch does not belong to the selected restaurant."
                )

        # Restaurant must belong to the specified organization
        if self.restaurant and self.organization:
            if self.restaurant.organization_id != self.organization.pk:
                raise ValidationError(
                    "The selected restaurant does not belong to the selected organization."
                )

        # Branch requires restaurant
        if self.branch and not self.restaurant:
            raise ValidationError(
                "A branch assignment requires a restaurant to be specified."
            )

        # Restaurant assignment requires organization
        if self.restaurant and not self.organization:
            raise ValidationError(
                "A restaurant assignment requires an organization to be specified."
            )

        # Validate against role scope
        if self.role_id:
            role = self.role
            if role.scope == Role.SCOPE_ORGANIZATION:
                if self.restaurant or self.branch:
                    raise ValidationError(
                        f"Role '{role.code}' has organization scope — "
                        "restaurant and branch must be empty."
                    )
                if not self.organization:
                    raise ValidationError(
                        f"Role '{role.code}' requires an organization."
                    )
            elif role.scope == Role.SCOPE_RESTAURANT:
                if self.branch:
                    raise ValidationError(
                        f"Role '{role.code}' has restaurant scope — branch must be empty."
                    )
                if not self.restaurant:
                    raise ValidationError(
                        f"Role '{role.code}' requires a restaurant."
                    )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
