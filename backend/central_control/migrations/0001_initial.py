# =============================================================================
# RestaurantFlow — Central Control Center Initial Migration
# Phase 15
# Generated manually (Python not available in CI environment)
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
        # ---- CentralControlSettings ----
        migrations.CreateModel(
            name="CentralControlSettings",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("organization", models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="central_control_settings",
                    to="organizations.organization",
                )),
                ("kitchen_delay_minutes", models.PositiveIntegerField(default=20)),
                ("kitchen_backlog_threshold", models.PositiveIntegerField(default=15)),
                ("low_stock_alert_enabled", models.BooleanField(default=True)),
                ("out_of_stock_alert_enabled", models.BooleanField(default=True)),
                ("payable_overdue_alert_enabled", models.BooleanField(default=True)),
                ("payment_failure_threshold", models.PositiveIntegerField(default=5)),
                ("counter_session_max_hours", models.PositiveIntegerField(default=16)),
                ("alert_escalation_enabled", models.BooleanField(default=True)),
                ("issue_auto_creation_enabled", models.BooleanField(default=True)),
            ],
            options={"verbose_name": "Central Control Settings", "verbose_name_plural": "Central Control Settings"},
        ),

        # ---- CentralAlert ----
        migrations.CreateModel(
            name="CentralAlert",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("organization", models.ForeignKey(
                    db_index=True, on_delete=django.db.models.deletion.PROTECT,
                    related_name="central_alerts", to="organizations.organization",
                )),
                ("restaurant", models.ForeignKey(
                    blank=True, db_index=True, null=True,
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="central_alerts", to="organizations.restaurant",
                )),
                ("branch", models.ForeignKey(
                    blank=True, db_index=True, null=True,
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="central_alerts", to="organizations.branch",
                )),
                ("alert_type", models.CharField(db_index=True, max_length=40)),
                ("severity", models.CharField(db_index=True, default="MEDIUM", max_length=10)),
                ("title", models.CharField(max_length=300)),
                ("message", models.TextField()),
                ("source_type", models.CharField(blank=True, db_index=True, max_length=30)),
                ("source_id", models.CharField(blank=True, db_index=True, max_length=100)),
                ("fingerprint", models.CharField(db_index=True, max_length=255)),
                ("status", models.CharField(db_index=True, default="OPEN", max_length=20)),
                ("detected_at", models.DateTimeField(db_index=True)),
                ("expires_at", models.DateTimeField(blank=True, db_index=True, null=True)),
                ("acknowledged_at", models.DateTimeField(blank=True, null=True)),
                ("acknowledged_by", models.ForeignKey(
                    blank=True, null=True, on_delete=django.db.models.deletion.PROTECT,
                    related_name="acknowledged_central_alerts", to=settings.AUTH_USER_MODEL,
                )),
                ("resolved_at", models.DateTimeField(blank=True, null=True)),
                ("resolved_by", models.ForeignKey(
                    blank=True, null=True, on_delete=django.db.models.deletion.PROTECT,
                    related_name="resolved_central_alerts", to=settings.AUTH_USER_MODEL,
                )),
                ("resolution_note", models.TextField(blank=True)),
                ("detection_count", models.PositiveIntegerField(default=1)),
                ("last_detected_at", models.DateTimeField(blank=True, null=True)),
            ],
            options={"verbose_name": "Central Alert", "verbose_name_plural": "Central Alerts", "ordering": ["-detected_at"]},
        ),
        migrations.AddConstraint(
            model_name="centralalert",
            constraint=models.UniqueConstraint(
                condition=models.Q(status__in=["OPEN", "ACKNOWLEDGED"]),
                fields=["organization", "fingerprint", "status"],
                name="unique_active_alert_per_fingerprint_per_org",
            ),
        ),
        migrations.AddIndex(
            model_name="centralalert",
            index=models.Index(fields=["organization", "status"], name="cc_alert_org_status_idx"),
        ),
        migrations.AddIndex(
            model_name="centralalert",
            index=models.Index(fields=["organization", "severity"], name="cc_alert_org_severity_idx"),
        ),
        migrations.AddIndex(
            model_name="centralalert",
            index=models.Index(fields=["organization", "alert_type"], name="cc_alert_org_type_idx"),
        ),
        migrations.AddIndex(
            model_name="centralalert",
            index=models.Index(fields=["organization", "status", "severity"], name="cc_alert_org_status_sev_idx"),
        ),
        migrations.AddIndex(
            model_name="centralalert",
            index=models.Index(fields=["restaurant", "status"], name="cc_alert_rest_status_idx"),
        ),
        migrations.AddIndex(
            model_name="centralalert",
            index=models.Index(fields=["branch", "status"], name="cc_alert_branch_status_idx"),
        ),
        migrations.AddIndex(
            model_name="centralalert",
            index=models.Index(fields=["alert_type", "status"], name="cc_alert_type_status_idx"),
        ),
        migrations.AddIndex(
            model_name="centralalert",
            index=models.Index(fields=["severity", "status"], name="cc_alert_sev_status_idx"),
        ),
        migrations.AddIndex(
            model_name="centralalert",
            index=models.Index(fields=["detected_at"], name="cc_alert_detected_idx"),
        ),
        migrations.AddIndex(
            model_name="centralalert",
            index=models.Index(fields=["source_type", "source_id"], name="cc_alert_source_idx"),
        ),
        migrations.AddIndex(
            model_name="centralalert",
            index=models.Index(fields=["fingerprint"], name="cc_alert_fingerprint_idx"),
        ),
        migrations.AddIndex(
            model_name="centralalert",
            index=models.Index(fields=["expires_at"], name="cc_alert_expires_idx"),
        ),

        # ---- EscalationRule ----
        migrations.CreateModel(
            name="EscalationRule",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("organization", models.ForeignKey(
                    db_index=True, on_delete=django.db.models.deletion.PROTECT,
                    related_name="escalation_rules", to="organizations.organization",
                )),
                ("restaurant", models.ForeignKey(
                    blank=True, db_index=True, null=True,
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="escalation_rules", to="organizations.restaurant",
                )),
                ("alert_type", models.CharField(db_index=True, max_length=40)),
                ("severity", models.CharField(db_index=True, max_length=10)),
                ("threshold_minutes", models.PositiveIntegerField(default=30)),
                ("auto_create_issue", models.BooleanField(default=True)),
                ("escalation_target_role", models.CharField(blank=True, max_length=50)),
                ("is_active", models.BooleanField(db_index=True, default=True)),
            ],
            options={"verbose_name": "Escalation Rule", "verbose_name_plural": "Escalation Rules", "ordering": ["alert_type", "severity"]},
        ),
        migrations.AddIndex(
            model_name="escalationrule",
            index=models.Index(fields=["organization", "is_active"], name="cc_escrule_org_active_idx"),
        ),
        migrations.AddIndex(
            model_name="escalationrule",
            index=models.Index(fields=["alert_type", "severity"], name="cc_escrule_type_sev_idx"),
        ),

        # ---- CentralIssue ----
        migrations.CreateModel(
            name="CentralIssue",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("organization", models.ForeignKey(
                    db_index=True, on_delete=django.db.models.deletion.PROTECT,
                    related_name="central_issues", to="organizations.organization",
                )),
                ("restaurant", models.ForeignKey(
                    blank=True, db_index=True, null=True,
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="central_issues", to="organizations.restaurant",
                )),
                ("branch", models.ForeignKey(
                    blank=True, db_index=True, null=True,
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="central_issues", to="organizations.branch",
                )),
                ("category", models.CharField(db_index=True, max_length=20)),
                ("title", models.CharField(max_length=300)),
                ("description", models.TextField()),
                ("severity", models.CharField(db_index=True, default="MEDIUM", max_length=10)),
                ("status", models.CharField(db_index=True, default="OPEN", max_length=20)),
                ("detected_from_alert", models.ForeignKey(
                    blank=True, db_index=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="created_issues", to="central_control.centralalert",
                )),
                ("created_by", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="created_central_issues", to=settings.AUTH_USER_MODEL,
                )),
                ("assigned_to", models.ForeignKey(
                    blank=True, db_index=True, null=True,
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="assigned_central_issues", to=settings.AUTH_USER_MODEL,
                )),
                ("resolved_by", models.ForeignKey(
                    blank=True, null=True, on_delete=django.db.models.deletion.PROTECT,
                    related_name="resolved_central_issues", to=settings.AUTH_USER_MODEL,
                )),
                ("closed_by", models.ForeignKey(
                    blank=True, null=True, on_delete=django.db.models.deletion.PROTECT,
                    related_name="closed_central_issues", to=settings.AUTH_USER_MODEL,
                )),
                ("cancelled_by", models.ForeignKey(
                    blank=True, null=True, on_delete=django.db.models.deletion.PROTECT,
                    related_name="cancelled_central_issues", to=settings.AUTH_USER_MODEL,
                )),
                ("due_at", models.DateTimeField(blank=True, db_index=True, null=True)),
                ("resolved_at", models.DateTimeField(blank=True, null=True)),
                ("closed_at", models.DateTimeField(blank=True, null=True)),
                ("cancelled_at", models.DateTimeField(blank=True, null=True)),
                ("resolution_note", models.TextField(blank=True)),
            ],
            options={"verbose_name": "Central Issue", "verbose_name_plural": "Central Issues", "ordering": ["-created_at"]},
        ),
        migrations.AddIndex(
            model_name="centralissue",
            index=models.Index(fields=["organization", "status"], name="cc_issue_org_status_idx"),
        ),
        migrations.AddIndex(
            model_name="centralissue",
            index=models.Index(fields=["organization", "severity"], name="cc_issue_org_sev_idx"),
        ),
        migrations.AddIndex(
            model_name="centralissue",
            index=models.Index(fields=["organization", "status", "severity"], name="cc_issue_org_status_sev_idx"),
        ),
        migrations.AddIndex(
            model_name="centralissue",
            index=models.Index(fields=["restaurant", "status"], name="cc_issue_rest_status_idx"),
        ),
        migrations.AddIndex(
            model_name="centralissue",
            index=models.Index(fields=["branch", "status"], name="cc_issue_branch_status_idx"),
        ),
        migrations.AddIndex(
            model_name="centralissue",
            index=models.Index(fields=["assigned_to", "status"], name="cc_issue_assignee_status_idx"),
        ),
        migrations.AddIndex(
            model_name="centralissue",
            index=models.Index(fields=["status", "created_at"], name="cc_issue_status_created_idx"),
        ),
        migrations.AddIndex(
            model_name="centralissue",
            index=models.Index(fields=["due_at"], name="cc_issue_due_idx"),
        ),
        migrations.AddIndex(
            model_name="centralissue",
            index=models.Index(fields=["severity", "status"], name="cc_issue_sev_status_idx"),
        ),

        # ---- CentralSystemEvent ----
        migrations.CreateModel(
            name="CentralSystemEvent",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("organization", models.ForeignKey(
                    db_index=True, on_delete=django.db.models.deletion.PROTECT,
                    related_name="system_events", to="organizations.organization",
                )),
                ("restaurant", models.ForeignKey(
                    blank=True, db_index=True, null=True,
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="system_events", to="organizations.restaurant",
                )),
                ("branch", models.ForeignKey(
                    blank=True, db_index=True, null=True,
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="system_events", to="organizations.branch",
                )),
                ("event_type", models.CharField(db_index=True, max_length=40)),
                ("severity", models.CharField(db_index=True, default="MEDIUM", max_length=10)),
                ("title", models.CharField(max_length=300)),
                ("description", models.TextField(blank=True)),
                ("alert", models.ForeignKey(
                    blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                    related_name="events", to="central_control.centralalert",
                )),
                ("issue", models.ForeignKey(
                    blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                    related_name="events", to="central_control.centralissue",
                )),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("occurred_at", models.DateTimeField(db_index=True)),
            ],
            options={"verbose_name": "Central System Event", "verbose_name_plural": "Central System Events", "ordering": ["-occurred_at"]},
        ),
        migrations.AddIndex(
            model_name="centralsystemevent",
            index=models.Index(fields=["organization", "occurred_at"], name="cc_event_org_occurred_idx"),
        ),
        migrations.AddIndex(
            model_name="centralsystemevent",
            index=models.Index(fields=["organization", "event_type"], name="cc_event_org_type_idx"),
        ),
        migrations.AddIndex(
            model_name="centralsystemevent",
            index=models.Index(fields=["organization", "severity"], name="cc_event_org_sev_idx"),
        ),
        migrations.AddIndex(
            model_name="centralsystemevent",
            index=models.Index(fields=["restaurant", "occurred_at"], name="cc_event_rest_occurred_idx"),
        ),
        migrations.AddIndex(
            model_name="centralsystemevent",
            index=models.Index(fields=["branch", "occurred_at"], name="cc_event_branch_occurred_idx"),
        ),
        migrations.AddIndex(
            model_name="centralsystemevent",
            index=models.Index(fields=["event_type", "occurred_at"], name="cc_event_type_occurred_idx"),
        ),

        # ---- CentralControlAuditLog ----
        migrations.CreateModel(
            name="CentralControlAuditLog",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("actor", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="central_control_audit_entries", to=settings.AUTH_USER_MODEL,
                )),
                ("action", models.CharField(db_index=True, max_length=50)),
                ("entity_type", models.CharField(db_index=True, max_length=50)),
                ("entity_id", models.UUIDField(blank=True, db_index=True, null=True)),
                ("organization", models.ForeignKey(
                    blank=True, db_index=True, null=True,
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="central_audit_logs", to="organizations.organization",
                )),
                ("restaurant", models.ForeignKey(
                    blank=True, null=True, on_delete=django.db.models.deletion.PROTECT,
                    related_name="central_audit_logs", to="organizations.restaurant",
                )),
                ("branch", models.ForeignKey(
                    blank=True, null=True, on_delete=django.db.models.deletion.PROTECT,
                    related_name="central_audit_logs", to="organizations.branch",
                )),
                ("old_status", models.CharField(blank=True, max_length=30)),
                ("new_status", models.CharField(blank=True, max_length=30)),
                ("metadata", models.JSONField(blank=True, default=dict)),
            ],
            options={"verbose_name": "Central Control Audit Log", "verbose_name_plural": "Central Control Audit Logs", "ordering": ["-created_at"]},
        ),
        migrations.AddIndex(
            model_name="centralcontrolauditlog",
            index=models.Index(fields=["actor", "created_at"], name="cc_audit_actor_created_idx"),
        ),
        migrations.AddIndex(
            model_name="centralcontrolauditlog",
            index=models.Index(fields=["action", "created_at"], name="cc_audit_action_created_idx"),
        ),
        migrations.AddIndex(
            model_name="centralcontrolauditlog",
            index=models.Index(fields=["entity_type", "entity_id"], name="cc_audit_entity_idx"),
        ),
        migrations.AddIndex(
            model_name="centralcontrolauditlog",
            index=models.Index(fields=["organization", "created_at"], name="cc_audit_org_created_idx"),
        ),
    ]
