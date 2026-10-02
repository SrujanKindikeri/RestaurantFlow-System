# =============================================================================
# RestaurantFlow — Custom User Model
# Phase 1 Foundation
#
# NOTE: This custom user model is established in Phase 1 to avoid the pain of
# changing AUTH_USER_MODEL after the first migration. Future phases will add
# role/permission/organization fields without restructuring the project.
# =============================================================================

import logging
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.db import models
from django.utils import timezone

logger = logging.getLogger("accounts")


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


class User(AbstractBaseUser, PermissionsMixin):
    """
    Custom User model for RestaurantFlow.

    Uses email as the primary identifier instead of username.
    Designed to support multi-tenant role assignment in later phases:

        User → Organization → Restaurant → Branch → Counter

    Phase 3 will add:
        - role (Company Head, Restaurant Owner, Manager, Cashier, Waiter, etc.)
        - organization FK
        - restaurant FK
        - branch FK
        - counter FK
    """

    # -------------------------------------------------------------------------
    # Core identity
    # -------------------------------------------------------------------------
    email = models.EmailField(unique=True, db_index=True)
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)

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

    # -------------------------------------------------------------------------
    # Phase 3 placeholders — NOT implemented yet, reserved for future use
    # role            = ...
    # organization    = ...
    # restaurant      = ...
    # branch          = ...
    # counter         = ...
    # -------------------------------------------------------------------------

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"
        ordering = ["-date_joined"]

    def __str__(self):
        return self.email

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip() or self.email
