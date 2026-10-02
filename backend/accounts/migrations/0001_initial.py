# =============================================================================
# RestaurantFlow — Accounts Initial Migration
# Phase 3
#
# Creates:
#   accounts_user
#   accounts_userprofile
#   accounts_permission
#   accounts_role
#   accounts_role_permissions   (M2M)
#   accounts_userroleassignment
# =============================================================================

import uuid
import django.contrib.auth.models
import django.db.models.deletion
import django.utils.timezone
import accounts.models
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
        ("organizations", "0001_initial"),
    ]

    operations = [
        # ------------------------------------------------------------------
        # accounts_user
        # ------------------------------------------------------------------
        migrations.CreateModel(
            name="User",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("password", models.CharField(max_length=128, verbose_name="password")),
                (
                    "last_login",
                    models.DateTimeField(
                        blank=True, null=True, verbose_name="last login"
                    ),
                ),
                (
                    "is_superuser",
                    models.BooleanField(
                        default=False,
                        verbose_name="superuser status",
                        help_text="Designates that this user has all permissions without explicitly assigning them.",
                    ),
                ),
                (
                    "email",
                    models.EmailField(db_index=True, max_length=254, unique=True),
                ),
                ("first_name", models.CharField(blank=True, max_length=150)),
                ("last_name", models.CharField(blank=True, max_length=150)),
                ("phone", models.CharField(blank=True, db_index=True, max_length=30)),
                ("is_active", models.BooleanField(default=True)),
                ("is_staff", models.BooleanField(default=False)),
                (
                    "date_joined",
                    models.DateTimeField(default=django.utils.timezone.now),
                ),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "groups",
                    models.ManyToManyField(
                        blank=True,
                        help_text="The groups this user belongs to.",
                        related_name="user_set",
                        related_query_name="user",
                        to="auth.group",
                        verbose_name="groups",
                    ),
                ),
                (
                    "user_permissions",
                    models.ManyToManyField(
                        blank=True,
                        help_text="Specific permissions for this user.",
                        related_name="user_set",
                        related_query_name="user",
                        to="auth.permission",
                        verbose_name="user permissions",
                    ),
                ),
            ],
            options={
                "verbose_name": "User",
                "verbose_name_plural": "Users",
                "ordering": ["-date_joined"],
            },
            managers=[
                ("objects", accounts.models.UserManager()),
            ],
        ),
        # ------------------------------------------------------------------
        # accounts_permission
        # ------------------------------------------------------------------
        migrations.CreateModel(
            name="Permission",
            fields=[
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True),
                ),
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "code",
                    models.CharField(db_index=True, max_length=100, unique=True),
                ),
                ("name", models.CharField(max_length=150)),
                ("description", models.TextField(blank=True)),
                ("module", models.CharField(db_index=True, max_length=50)),
                ("action", models.CharField(db_index=True, max_length=50)),
                ("is_active", models.BooleanField(db_index=True, default=True)),
            ],
            options={
                "verbose_name": "Permission",
                "verbose_name_plural": "Permissions",
                "ordering": ["module", "action"],
            },
        ),
        # ------------------------------------------------------------------
        # accounts_role
        # ------------------------------------------------------------------
        migrations.CreateModel(
            name="Role",
            fields=[
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True),
                ),
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("name", models.CharField(max_length=100)),
                (
                    "code",
                    models.CharField(db_index=True, max_length=50, unique=True),
                ),
                ("description", models.TextField(blank=True)),
                (
                    "scope",
                    models.CharField(
                        choices=[
                            ("organization", "Organization"),
                            ("restaurant", "Restaurant"),
                            ("branch", "Branch"),
                        ],
                        db_index=True,
                        default="branch",
                        max_length=20,
                    ),
                ),
                ("is_system_role", models.BooleanField(default=False)),
                ("is_active", models.BooleanField(db_index=True, default=True)),
                (
                    "permissions",
                    models.ManyToManyField(
                        blank=True,
                        related_name="roles",
                        to="accounts.permission",
                    ),
                ),
            ],
            options={
                "verbose_name": "Role",
                "verbose_name_plural": "Roles",
                "ordering": ["name"],
            },
        ),
        # ------------------------------------------------------------------
        # accounts_userprofile
        # ------------------------------------------------------------------
        migrations.CreateModel(
            name="UserProfile",
            fields=[
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True),
                ),
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("display_name", models.CharField(blank=True, max_length=150)),
                (
                    "employee_code",
                    models.CharField(blank=True, db_index=True, max_length=50),
                ),
                (
                    "profile_photo",
                    models.ImageField(
                        blank=True, null=True, upload_to="profile_photos/"
                    ),
                ),
                ("is_active", models.BooleanField(default=True)),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="profile",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "User Profile",
                "verbose_name_plural": "User Profiles",
            },
        ),
        # ------------------------------------------------------------------
        # accounts_userroleassignment
        # ------------------------------------------------------------------
        migrations.CreateModel(
            name="UserRoleAssignment",
            fields=[
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True),
                ),
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("is_active", models.BooleanField(db_index=True, default=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="role_assignments",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "role",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="assignments",
                        to="accounts.role",
                    ),
                ),
                (
                    "organization",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="user_assignments",
                        to="organizations.organization",
                    ),
                ),
                (
                    "restaurant",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="user_assignments",
                        to="organizations.restaurant",
                    ),
                ),
                (
                    "branch",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="user_assignments",
                        to="organizations.branch",
                    ),
                ),
            ],
            options={
                "verbose_name": "User Role Assignment",
                "verbose_name_plural": "User Role Assignments",
                "ordering": ["-created_at"],
            },
        ),
        # ------------------------------------------------------------------
        # Indexes
        # ------------------------------------------------------------------
        migrations.AddIndex(
            model_name="user",
            index=models.Index(fields=["email"], name="accounts_us_email_idx"),
        ),
        migrations.AddIndex(
            model_name="user",
            index=models.Index(fields=["is_active"], name="accounts_us_is_acti_idx"),
        ),
        migrations.AddIndex(
            model_name="permission",
            index=models.Index(
                fields=["module", "action"], name="accounts_pe_module_action_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="permission",
            index=models.Index(
                fields=["is_active"], name="accounts_pe_is_acti_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="role",
            index=models.Index(fields=["code"], name="accounts_ro_code_idx"),
        ),
        migrations.AddIndex(
            model_name="role",
            index=models.Index(fields=["scope"], name="accounts_ro_scope_idx"),
        ),
        migrations.AddIndex(
            model_name="role",
            index=models.Index(fields=["is_active"], name="accounts_ro_is_acti_idx"),
        ),
        migrations.AddIndex(
            model_name="userroleassignment",
            index=models.Index(
                fields=["user", "is_active"], name="accounts_ur_user_is_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="userroleassignment",
            index=models.Index(
                fields=["role", "is_active"], name="accounts_ur_role_is_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="userroleassignment",
            index=models.Index(
                fields=["organization", "is_active"],
                name="accounts_ur_org_is_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="userroleassignment",
            index=models.Index(
                fields=["restaurant", "is_active"],
                name="accounts_ur_rest_is_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="userroleassignment",
            index=models.Index(
                fields=["branch", "is_active"], name="accounts_ur_branch_is_idx"
            ),
        ),
    ]
