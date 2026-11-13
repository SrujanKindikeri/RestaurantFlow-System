# =============================================================================
# RestaurantFlow — Phase 21 Security Audit Log Migration
#
# Creates the SecurityAuditLog model — an immutable, append-only audit trail
# for security-relevant events (login, logout, password changes, role
# assignments, account management, security alerts).
# =============================================================================

import uuid

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
        ("organizations", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="SecurityAuditLog",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
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
                    "event",
                    models.CharField(
                        choices=[
                            ("login", "Login"),
                            ("login_failed", "Login Failed"),
                            ("logout", "Logout"),
                            ("password_change", "Password Change"),
                            ("password_reset_request", "Password Reset Requested"),
                            ("password_reset_complete", "Password Reset Completed"),
                            ("account_disabled", "Account Disabled"),
                            ("account_reactivated", "Account Reactivated"),
                            ("role_assigned", "Role Assigned"),
                            ("role_revoked", "Role Revoked"),
                            ("permission_denied", "Permission Denied"),
                            ("session_revoked", "Session Revoked"),
                            ("security_alert", "Security Alert"),
                            ("user_registered", "User Registered"),
                            ("user_created", "User Created"),
                            ("login_lockout", "Login Lockout"),
                        ],
                        db_index=True,
                        max_length=40,
                    ),
                ),
                (
                    "outcome",
                    models.CharField(
                        choices=[
                            ("success", "Success"),
                            ("failure", "Failure"),
                        ],
                        db_index=True,
                        default="success",
                        max_length=10,
                    ),
                ),
                ("ip_address", models.GenericIPAddressField(blank=True, null=True)),
                ("user_agent", models.TextField(blank=True)),
                (
                    "request_id",
                    models.CharField(blank=True, db_index=True, max_length=100),
                ),
                (
                    "metadata",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text=(
                            "Safe, non-sensitive context: role code, permission code, "
                            "reason, etc. NEVER store passwords, tokens, session IDs, "
                            "or secret keys."
                        ),
                    ),
                ),
                (
                    "actor",
                    models.ForeignKey(
                        blank=True,
                        db_index=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="security_audit_logs",
                        to="accounts.user",
                    ),
                ),
                (
                    "target_user",
                    models.ForeignKey(
                        blank=True,
                        db_index=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="security_audit_logs_as_target",
                        to="accounts.user",
                    ),
                ),
                (
                    "organization",
                    models.ForeignKey(
                        blank=True,
                        db_index=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="security_audit_logs",
                        to="organizations.organization",
                    ),
                ),
            ],
            options={
                "verbose_name": "Security Audit Log",
                "verbose_name_plural": "Security Audit Logs",
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(fields=["event", "created_at"], name="accounts_se_event_idx"),
                    models.Index(fields=["actor", "created_at"], name="accounts_se_actor_idx"),
                    models.Index(fields=["target_user", "created_at"], name="accounts_se_target_idx"),
                    models.Index(fields=["organization", "created_at"], name="accounts_se_org_idx"),
                    models.Index(fields=["outcome", "created_at"], name="accounts_se_outcome_idx"),
                    models.Index(fields=["ip_address", "created_at"], name="accounts_se_ip_idx"),
                ],
            },
        ),
    ]
