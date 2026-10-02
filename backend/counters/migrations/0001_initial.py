# =============================================================================
# RestaurantFlow — Counters Initial Migration
# Phase 4
# Generated manually (Docker not available during authoring).
# =============================================================================

import uuid
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("organizations", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # ------------------------------------------------------------------
        # Shift
        # ------------------------------------------------------------------
        migrations.CreateModel(
            name="Shift",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=100)),
                ("start_time", models.TimeField()),
                ("end_time", models.TimeField()),
                ("is_active", models.BooleanField(db_index=True, default=True)),
                (
                    "branch",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="shifts",
                        to="organizations.branch",
                    ),
                ),
            ],
            options={
                "verbose_name": "Shift",
                "verbose_name_plural": "Shifts",
                "ordering": ["branch", "start_time"],
            },
        ),
        migrations.AddIndex(
            model_name="shift",
            index=models.Index(fields=["branch", "is_active"], name="shift_branch_active_idx"),
        ),

        # ------------------------------------------------------------------
        # Counter
        # ------------------------------------------------------------------
        migrations.CreateModel(
            name="Counter",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=150)),
                ("code", models.CharField(db_index=True, max_length=20)),
                ("description", models.TextField(blank=True)),
                (
                    "counter_type",
                    models.CharField(
                        choices=[
                            ("MAIN_BILLING", "Main Billing"),
                            ("TAKEAWAY", "Takeaway"),
                            ("SNACKS", "Snacks"),
                            ("DRIVE_THROUGH", "Drive Through"),
                            ("OTHER", "Other"),
                        ],
                        db_index=True,
                        default="MAIN_BILLING",
                        max_length=20,
                    ),
                ),
                ("location", models.CharField(blank=True, max_length=200)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("ACTIVE", "Active"),
                            ("INACTIVE", "Inactive"),
                            ("MAINTENANCE", "Maintenance"),
                        ],
                        db_index=True,
                        default="ACTIVE",
                        max_length=20,
                    ),
                ),
                ("is_active", models.BooleanField(db_index=True, default=True)),
                (
                    "branch",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="counters",
                        to="organizations.branch",
                    ),
                ),
            ],
            options={
                "verbose_name": "Counter",
                "verbose_name_plural": "Counters",
                "ordering": ["branch", "code"],
            },
        ),
        migrations.AddConstraint(
            model_name="counter",
            constraint=models.UniqueConstraint(
                fields=["branch", "code"],
                name="unique_counter_code_per_branch",
            ),
        ),
        migrations.AddIndex(
            model_name="counter",
            index=models.Index(fields=["branch", "status"], name="counter_branch_status_idx"),
        ),
        migrations.AddIndex(
            model_name="counter",
            index=models.Index(fields=["branch", "is_active"], name="counter_branch_active_idx"),
        ),
        migrations.AddIndex(
            model_name="counter",
            index=models.Index(fields=["branch", "code"], name="counter_branch_code_idx"),
        ),

        # ------------------------------------------------------------------
        # CounterAssignment
        # ------------------------------------------------------------------
        migrations.CreateModel(
            name="CounterAssignment",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("assigned_at", models.DateTimeField(auto_now_add=True)),
                ("expires_at", models.DateTimeField(blank=True, null=True)),
                ("is_active", models.BooleanField(db_index=True, default=True)),
                (
                    "counter",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="assignments",
                        to="counters.counter",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="counter_assignments",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "assigned_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="counter_assignments_made",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Counter Assignment",
                "verbose_name_plural": "Counter Assignments",
                "ordering": ["-assigned_at"],
            },
        ),
        migrations.AddIndex(
            model_name="counterassignment",
            index=models.Index(fields=["counter", "is_active"], name="assignment_counter_active_idx"),
        ),
        migrations.AddIndex(
            model_name="counterassignment",
            index=models.Index(fields=["user", "is_active"], name="assignment_user_active_idx"),
        ),
        migrations.AddIndex(
            model_name="counterassignment",
            index=models.Index(fields=["counter", "user", "is_active"], name="assignment_counter_user_idx"),
        ),

        # ------------------------------------------------------------------
        # CounterSession
        # ------------------------------------------------------------------
        migrations.CreateModel(
            name="CounterSession",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("opened_at", models.DateTimeField(auto_now_add=True)),
                ("closed_at", models.DateTimeField(blank=True, null=True)),
                (
                    "opening_cash",
                    models.DecimalField(decimal_places=2, default="0.00", max_digits=12),
                ),
                (
                    "expected_cash",
                    models.DecimalField(
                        decimal_places=2,
                        default="0.00",
                        help_text="Phase 4: equals opening_cash. Future phases will add sales/refunds/adjustments.",
                        max_digits=12,
                    ),
                ),
                (
                    "actual_cash",
                    models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True),
                ),
                (
                    "cash_difference",
                    models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        help_text="actual_cash - expected_cash. Calculated by backend; never trusted from client.",
                        max_digits=12,
                        null=True,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("OPEN", "Open"),
                            ("CLOSED", "Closed"),
                            ("FORCE_CLOSED", "Force Closed"),
                        ],
                        db_index=True,
                        default="OPEN",
                        max_length=20,
                    ),
                ),
                ("closing_note", models.TextField(blank=True)),
                (
                    "counter",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="sessions",
                        to="counters.counter",
                    ),
                ),
                (
                    "shift",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="sessions",
                        to="counters.shift",
                    ),
                ),
                (
                    "opened_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="opened_sessions",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "closed_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="closed_sessions",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Counter Session",
                "verbose_name_plural": "Counter Sessions",
                "ordering": ["-opened_at"],
            },
        ),
        migrations.AddConstraint(
            model_name="countersession",
            constraint=models.UniqueConstraint(
                condition=models.Q(status="OPEN"),
                fields=["counter"],
                name="unique_open_session_per_counter",
            ),
        ),
        migrations.AddIndex(
            model_name="countersession",
            index=models.Index(fields=["counter", "status"], name="session_counter_status_idx"),
        ),
        migrations.AddIndex(
            model_name="countersession",
            index=models.Index(fields=["opened_by", "status"], name="session_opener_status_idx"),
        ),
        migrations.AddIndex(
            model_name="countersession",
            index=models.Index(fields=["counter", "opened_at"], name="session_counter_opened_idx"),
        ),
    ]
