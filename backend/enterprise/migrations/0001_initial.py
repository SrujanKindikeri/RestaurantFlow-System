# =============================================================================
# RestaurantFlow — Enterprise Initial Migration
# Phase 20: Multi-Branch Enterprise Operations & Configuration
#
# Models created:
#   BranchOperationalStatus
#   BranchOperatingHour
#   BranchClosure
#   EnterpriseConfiguration
#   ConfigurationChange
#   MenuRollout
#   MenuRolloutBranch
#   StaffBranchAssignment
#   StaffTransfer
#   ApprovalPolicy
#   EnterpriseAuditLog
# =============================================================================

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("organizations", "0001_initial"),
        ("accounts", "0001_initial"),
        ("menu", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [

        # =====================================================================
        # BranchOperationalStatus
        # =====================================================================
        migrations.CreateModel(
            name="BranchOperationalStatus",
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
                    "status",
                    models.CharField(
                        choices=[
                            ("ACTIVE", "Active"),
                            ("TEMPORARILY_CLOSED", "Temporarily Closed"),
                            ("SCHEDULED_CLOSURE", "Scheduled Closure"),
                            ("MAINTENANCE", "Under Maintenance"),
                            ("INACTIVE", "Inactive"),
                        ],
                        db_index=True,
                        default="ACTIVE",
                        max_length=30,
                    ),
                ),
                ("status_changed_at", models.DateTimeField(blank=True, null=True)),
                ("status_reason", models.TextField(blank=True)),
                (
                    "branch",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="operational_status",
                        to="organizations.branch",
                    ),
                ),
                (
                    "status_changed_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="branch_status_changes",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Branch Operational Status",
                "verbose_name_plural": "Branch Operational Statuses",
            },
        ),
        migrations.AddIndex(
            model_name="branchoperationalstatus",
            index=models.Index(fields=["status"], name="enterprise_branchop_status_idx"),
        ),
        migrations.AddIndex(
            model_name="branchoperationalstatus",
            index=models.Index(fields=["branch", "status"], name="enterprise_branchop_branch_status_idx"),
        ),

        # =====================================================================
        # BranchOperatingHour
        # =====================================================================
        migrations.CreateModel(
            name="BranchOperatingHour",
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
                    "day_of_week",
                    models.CharField(
                        choices=[
                            ("MONDAY", "Monday"),
                            ("TUESDAY", "Tuesday"),
                            ("WEDNESDAY", "Wednesday"),
                            ("THURSDAY", "Thursday"),
                            ("FRIDAY", "Friday"),
                            ("SATURDAY", "Saturday"),
                            ("SUNDAY", "Sunday"),
                        ],
                        db_index=True,
                        max_length=10,
                    ),
                ),
                ("opening_time", models.TimeField(blank=True, null=True)),
                ("closing_time", models.TimeField(blank=True, null=True)),
                ("is_closed", models.BooleanField(default=False)),
                (
                    "branch",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="operating_hours",
                        to="organizations.branch",
                    ),
                ),
            ],
            options={
                "verbose_name": "Branch Operating Hour",
                "verbose_name_plural": "Branch Operating Hours",
                "ordering": ["branch", "day_of_week"],
            },
        ),
        migrations.AddConstraint(
            model_name="branchoperatinghour",
            constraint=models.UniqueConstraint(
                fields=["branch", "day_of_week"],
                name="unique_branch_operating_hour_per_day",
            ),
        ),
        migrations.AddIndex(
            model_name="branchoperatinghour",
            index=models.Index(fields=["branch", "day_of_week"], name="enterprise_branchhour_branch_day_idx"),
        ),
        migrations.AddIndex(
            model_name="branchoperatinghour",
            index=models.Index(fields=["branch", "is_closed"], name="enterprise_branchhour_branch_closed_idx"),
        ),

        # =====================================================================
        # BranchClosure
        # =====================================================================
        migrations.CreateModel(
            name="BranchClosure",
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
                    "closure_type",
                    models.CharField(
                        choices=[
                            ("HOLIDAY", "Public Holiday"),
                            ("MAINTENANCE", "Maintenance"),
                            ("PRIVATE_EVENT", "Private Event"),
                            ("EMERGENCY", "Emergency"),
                            ("OTHER", "Other"),
                        ],
                        db_index=True,
                        max_length=20,
                    ),
                ),
                ("start_datetime", models.DateTimeField(db_index=True)),
                ("end_datetime", models.DateTimeField(db_index=True)),
                ("reason", models.TextField()),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("DRAFT", "Draft"),
                            ("PENDING_APPROVAL", "Pending Approval"),
                            ("APPROVED", "Approved"),
                            ("REJECTED", "Rejected"),
                            ("CANCELLED", "Cancelled"),
                            ("ACTIVE", "Active"),
                            ("COMPLETED", "Completed"),
                        ],
                        db_index=True,
                        default="DRAFT",
                        max_length=20,
                    ),
                ),
                ("approved_at", models.DateTimeField(blank=True, null=True)),
                ("rejected_at", models.DateTimeField(blank=True, null=True)),
                ("rejection_reason", models.TextField(blank=True)),
                (
                    "branch",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="closures",
                        to="organizations.branch",
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="created_closures",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "approved_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="approved_closures",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Branch Closure",
                "verbose_name_plural": "Branch Closures",
                "ordering": ["-start_datetime"],
            },
        ),
        migrations.AddIndex(
            model_name="branchclosure",
            index=models.Index(fields=["branch", "status"], name="enterprise_closure_branch_status_idx"),
        ),
        migrations.AddIndex(
            model_name="branchclosure",
            index=models.Index(fields=["branch", "start_datetime"], name="enterprise_closure_branch_start_idx"),
        ),
        migrations.AddIndex(
            model_name="branchclosure",
            index=models.Index(fields=["branch", "end_datetime"], name="enterprise_closure_branch_end_idx"),
        ),
        migrations.AddIndex(
            model_name="branchclosure",
            index=models.Index(fields=["status", "start_datetime"], name="enterprise_closure_status_start_idx"),
        ),

        # =====================================================================
        # EnterpriseConfiguration
        # =====================================================================
        migrations.CreateModel(
            name="EnterpriseConfiguration",
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
                    "configuration_key",
                    models.CharField(db_index=True, max_length=100),
                ),
                ("configuration_value", models.TextField()),
                (
                    "value_type",
                    models.CharField(
                        choices=[
                            ("STRING", "String"),
                            ("INTEGER", "Integer"),
                            ("DECIMAL", "Decimal"),
                            ("BOOLEAN", "Boolean"),
                            ("JSON", "JSON"),
                        ],
                        default="STRING",
                        max_length=10,
                    ),
                ),
                ("is_active", models.BooleanField(db_index=True, default=True)),
                ("version", models.PositiveIntegerField(default=1)),
                (
                    "company",
                    models.ForeignKey(
                        db_index=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="enterprise_configurations",
                        to="organizations.organization",
                    ),
                ),
                (
                    "restaurant",
                    models.ForeignKey(
                        blank=True,
                        db_index=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="enterprise_configurations",
                        to="organizations.restaurant",
                    ),
                ),
                (
                    "branch",
                    models.ForeignKey(
                        blank=True,
                        db_index=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="enterprise_configurations",
                        to="organizations.branch",
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="created_configurations",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="updated_configurations",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Enterprise Configuration",
                "verbose_name_plural": "Enterprise Configurations",
                "ordering": ["company", "restaurant", "branch", "configuration_key"],
            },
        ),
        migrations.AddConstraint(
            model_name="enterpriseconfiguration",
            constraint=models.UniqueConstraint(
                condition=models.Q(is_active=True, restaurant__isnull=True, branch__isnull=True),
                fields=["company", "configuration_key"],
                name="unique_active_company_config_key",
            ),
        ),
        migrations.AddConstraint(
            model_name="enterpriseconfiguration",
            constraint=models.UniqueConstraint(
                condition=models.Q(is_active=True, branch__isnull=True),
                fields=["company", "restaurant", "configuration_key"],
                name="unique_active_restaurant_config_key",
            ),
        ),
        migrations.AddConstraint(
            model_name="enterpriseconfiguration",
            constraint=models.UniqueConstraint(
                condition=models.Q(is_active=True),
                fields=["company", "restaurant", "branch", "configuration_key"],
                name="unique_active_branch_config_key",
            ),
        ),
        migrations.AddIndex(
            model_name="enterpriseconfiguration",
            index=models.Index(
                fields=["company", "configuration_key", "is_active"],
                name="enterprise_config_co_key_active_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="enterpriseconfiguration",
            index=models.Index(
                fields=["company", "restaurant", "configuration_key", "is_active"],
                name="enterprise_config_rest_key_active_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="enterpriseconfiguration",
            index=models.Index(
                fields=["company", "restaurant", "branch", "configuration_key", "is_active"],
                name="enterprise_config_br_key_active_idx",
            ),
        ),

        # =====================================================================
        # ConfigurationChange
        # =====================================================================
        migrations.CreateModel(
            name="ConfigurationChange",
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
                ("configuration_key", models.CharField(db_index=True, max_length=100)),
                ("old_value", models.TextField(blank=True)),
                ("new_value", models.TextField()),
                ("version", models.PositiveIntegerField()),
                ("change_reason", models.TextField(blank=True)),
                (
                    "scope",
                    models.CharField(
                        choices=[
                            ("COMPANY", "Company"),
                            ("RESTAURANT", "Restaurant"),
                            ("BRANCH", "Branch"),
                        ],
                        db_index=True,
                        default="COMPANY",
                        max_length=20,
                    ),
                ),
                (
                    "company",
                    models.ForeignKey(
                        db_index=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="configuration_changes",
                        to="organizations.organization",
                    ),
                ),
                (
                    "restaurant",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="configuration_changes",
                        to="organizations.restaurant",
                    ),
                ),
                (
                    "branch",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="configuration_changes",
                        to="organizations.branch",
                    ),
                ),
                (
                    "changed_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="configuration_changes",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Configuration Change",
                "verbose_name_plural": "Configuration Changes",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="configurationchange",
            index=models.Index(
                fields=["company", "configuration_key", "created_at"],
                name="enterprise_cfgchange_co_key_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="configurationchange",
            index=models.Index(
                fields=["company", "restaurant", "branch", "configuration_key"],
                name="enterprise_cfgchange_scope_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="configurationchange",
            index=models.Index(
                fields=["changed_by", "created_at"],
                name="enterprise_cfgchange_user_idx",
            ),
        ),

        # =====================================================================
        # MenuRollout
        # =====================================================================
        migrations.CreateModel(
            name="MenuRollout",
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
                    "rollout_type",
                    models.CharField(
                        choices=[
                            ("MENU_AVAILABILITY", "Menu Item Availability"),
                            ("PRICE", "Price Rollout"),
                        ],
                        db_index=True,
                        default="MENU_AVAILABILITY",
                        max_length=30,
                    ),
                ),
                (
                    "new_price",
                    models.DecimalField(
                        blank=True, decimal_places=2, max_digits=12, null=True
                    ),
                ),
                ("is_available", models.BooleanField(blank=True, null=True)),
                ("force_override", models.BooleanField(default=False)),
                (
                    "target_scope",
                    models.CharField(
                        choices=[
                            ("ALL_BRANCHES", "All Branches"),
                            ("SELECTED_BRANCHES", "Selected Branches"),
                        ],
                        default="ALL_BRANCHES",
                        max_length=20,
                    ),
                ),
                ("effective_from", models.DateTimeField(blank=True, null=True)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("DRAFT", "Draft"),
                            ("PENDING_APPROVAL", "Pending Approval"),
                            ("APPROVED", "Approved"),
                            ("SCHEDULED", "Scheduled"),
                            ("RUNNING", "Running"),
                            ("COMPLETED", "Completed"),
                            ("PARTIALLY_COMPLETED", "Partially Completed"),
                            ("FAILED", "Failed"),
                            ("CANCELLED", "Cancelled"),
                        ],
                        db_index=True,
                        default="DRAFT",
                        max_length=25,
                    ),
                ),
                ("approved_at", models.DateTimeField(blank=True, null=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("notes", models.TextField(blank=True)),
                (
                    "restaurant",
                    models.ForeignKey(
                        db_index=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="menu_rollouts",
                        to="organizations.restaurant",
                    ),
                ),
                (
                    "menu_item",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="rollouts",
                        to="menu.menuitem",
                    ),
                ),
                (
                    "source_branch",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="sourced_rollouts",
                        to="organizations.branch",
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="created_rollouts",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "approved_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="approved_rollouts",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "target_branches",
                    models.ManyToManyField(
                        blank=True,
                        related_name="targeted_rollouts",
                        to="organizations.branch",
                    ),
                ),
            ],
            options={
                "verbose_name": "Menu Rollout",
                "verbose_name_plural": "Menu Rollouts",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="menurollout",
            index=models.Index(fields=["restaurant", "status"], name="enterprise_rollout_rest_status_idx"),
        ),
        migrations.AddIndex(
            model_name="menurollout",
            index=models.Index(fields=["restaurant", "menu_item", "status"], name="enterprise_rollout_rest_item_idx"),
        ),
        migrations.AddIndex(
            model_name="menurollout",
            index=models.Index(fields=["status", "effective_from"], name="enterprise_rollout_status_eff_idx"),
        ),

        # =====================================================================
        # MenuRolloutBranch
        # =====================================================================
        migrations.CreateModel(
            name="MenuRolloutBranch",
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
                    "result",
                    models.CharField(
                        choices=[
                            ("SUCCESS", "Success"),
                            ("FAILED", "Failed"),
                            ("SKIPPED", "Skipped"),
                            ("SKIPPED_OVERRIDE", "Skipped — Branch Override Preserved"),
                        ],
                        db_index=True,
                        max_length=20,
                    ),
                ),
                ("old_value", models.TextField(blank=True)),
                ("new_value", models.TextField(blank=True)),
                ("failure_reason", models.TextField(blank=True)),
                (
                    "rollout",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="branch_results",
                        to="enterprise.menurollout",
                    ),
                ),
                (
                    "branch",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="rollout_results",
                        to="organizations.branch",
                    ),
                ),
            ],
            options={
                "verbose_name": "Menu Rollout Branch Result",
                "verbose_name_plural": "Menu Rollout Branch Results",
            },
        ),
        migrations.AddConstraint(
            model_name="menurolloutbranch",
            constraint=models.UniqueConstraint(
                fields=["rollout", "branch"],
                name="unique_rollout_branch_result",
            ),
        ),
        migrations.AddIndex(
            model_name="menurolloutbranch",
            index=models.Index(fields=["rollout", "result"], name="enterprise_rolloutbr_rollout_result_idx"),
        ),
        migrations.AddIndex(
            model_name="menurolloutbranch",
            index=models.Index(fields=["branch", "result"], name="enterprise_rolloutbr_branch_result_idx"),
        ),

        # =====================================================================
        # StaffBranchAssignment
        # =====================================================================
        migrations.CreateModel(
            name="StaffBranchAssignment",
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
                ("assigned_at", models.DateTimeField(auto_now_add=True)),
                ("start_date", models.DateField(blank=True, null=True)),
                ("end_date", models.DateField(blank=True, null=True)),
                ("is_primary", models.BooleanField(db_index=True, default=True)),
                ("is_active", models.BooleanField(db_index=True, default=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="branch_assignments",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "restaurant",
                    models.ForeignKey(
                        db_index=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="staff_assignments",
                        to="organizations.restaurant",
                    ),
                ),
                (
                    "branch",
                    models.ForeignKey(
                        db_index=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="staff_assignments",
                        to="organizations.branch",
                    ),
                ),
                (
                    "role",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="branch_assignments",
                        to="accounts.role",
                    ),
                ),
                (
                    "assigned_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="staff_assignments_made",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Staff Branch Assignment",
                "verbose_name_plural": "Staff Branch Assignments",
                "ordering": ["-assigned_at"],
            },
        ),
        migrations.AddConstraint(
            model_name="staffbranchassignment",
            constraint=models.UniqueConstraint(
                condition=models.Q(is_primary=True, is_active=True),
                fields=["user", "restaurant"],
                name="unique_primary_branch_assignment",
            ),
        ),
        migrations.AddIndex(
            model_name="staffbranchassignment",
            index=models.Index(fields=["user", "restaurant", "is_active"], name="enterprise_staffassign_user_rest_idx"),
        ),
        migrations.AddIndex(
            model_name="staffbranchassignment",
            index=models.Index(fields=["branch", "is_active"], name="enterprise_staffassign_branch_idx"),
        ),
        migrations.AddIndex(
            model_name="staffbranchassignment",
            index=models.Index(fields=["restaurant", "is_active"], name="enterprise_staffassign_rest_idx"),
        ),
        migrations.AddIndex(
            model_name="staffbranchassignment",
            index=models.Index(fields=["user", "is_primary", "is_active"], name="enterprise_staffassign_primary_idx"),
        ),

        # =====================================================================
        # StaffTransfer
        # =====================================================================
        migrations.CreateModel(
            name="StaffTransfer",
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
                ("reason", models.TextField()),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("REQUESTED", "Requested"),
                            ("APPROVED", "Approved"),
                            ("REJECTED", "Rejected"),
                            ("COMPLETED", "Completed"),
                            ("CANCELLED", "Cancelled"),
                        ],
                        db_index=True,
                        default="REQUESTED",
                        max_length=15,
                    ),
                ),
                ("requested_at", models.DateTimeField(auto_now_add=True)),
                ("approved_at", models.DateTimeField(blank=True, null=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("rejected_at", models.DateTimeField(blank=True, null=True)),
                ("rejection_reason", models.TextField(blank=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="staff_transfers",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "restaurant",
                    models.ForeignKey(
                        db_index=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="staff_transfers",
                        to="organizations.restaurant",
                    ),
                ),
                (
                    "source_branch",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="outgoing_transfers",
                        to="organizations.branch",
                    ),
                ),
                (
                    "destination_branch",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="incoming_transfers",
                        to="organizations.branch",
                    ),
                ),
                (
                    "requested_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="transfer_requests_made",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "approved_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="transfer_approvals",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Staff Transfer",
                "verbose_name_plural": "Staff Transfers",
                "ordering": ["-requested_at"],
            },
        ),
        migrations.AddIndex(
            model_name="stafftransfer",
            index=models.Index(fields=["user", "status"], name="enterprise_transfer_user_status_idx"),
        ),
        migrations.AddIndex(
            model_name="stafftransfer",
            index=models.Index(fields=["restaurant", "status"], name="enterprise_transfer_rest_status_idx"),
        ),
        migrations.AddIndex(
            model_name="stafftransfer",
            index=models.Index(fields=["source_branch", "status"], name="enterprise_transfer_src_status_idx"),
        ),
        migrations.AddIndex(
            model_name="stafftransfer",
            index=models.Index(fields=["destination_branch", "status"], name="enterprise_transfer_dst_status_idx"),
        ),

        # =====================================================================
        # ApprovalPolicy
        # =====================================================================
        migrations.CreateModel(
            name="ApprovalPolicy",
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
                    "policy_type",
                    models.CharField(
                        choices=[
                            ("EXPENSE", "Expense"),
                            ("DISCOUNT", "Discount"),
                            ("REFUND", "Refund"),
                            ("WASTAGE", "Wastage"),
                            ("STOCK_TRANSFER", "Stock Transfer"),
                            ("CONFIGURATION", "Configuration Change"),
                            ("PRICE_ROLLOUT", "Price Rollout"),
                        ],
                        db_index=True,
                        max_length=20,
                    ),
                ),
                (
                    "threshold_amount",
                    models.DecimalField(
                        blank=True, decimal_places=2, max_digits=12, null=True
                    ),
                ),
                (
                    "threshold_percentage",
                    models.DecimalField(
                        blank=True, decimal_places=2, max_digits=5, null=True
                    ),
                ),
                ("required_permission", models.CharField(max_length=100)),
                ("is_active", models.BooleanField(db_index=True, default=True)),
                (
                    "company",
                    models.ForeignKey(
                        db_index=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="approval_policies",
                        to="organizations.organization",
                    ),
                ),
                (
                    "restaurant",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="approval_policies",
                        to="organizations.restaurant",
                    ),
                ),
                (
                    "branch",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="approval_policies",
                        to="organizations.branch",
                    ),
                ),
                (
                    "required_role",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="approval_policies",
                        to="accounts.role",
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="created_approval_policies",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="updated_approval_policies",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Approval Policy",
                "verbose_name_plural": "Approval Policies",
                "ordering": ["company", "policy_type"],
            },
        ),
        migrations.AddIndex(
            model_name="approvalpolicy",
            index=models.Index(
                fields=["company", "policy_type", "is_active"],
                name="enterprise_policy_co_type_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="approvalpolicy",
            index=models.Index(
                fields=["company", "restaurant", "policy_type", "is_active"],
                name="enterprise_policy_rest_type_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="approvalpolicy",
            index=models.Index(
                fields=["company", "restaurant", "branch", "policy_type", "is_active"],
                name="enterprise_policy_br_type_idx",
            ),
        ),

        # =====================================================================
        # EnterpriseAuditLog
        # =====================================================================
        migrations.CreateModel(
            name="EnterpriseAuditLog",
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
                    "action",
                    models.CharField(db_index=True, max_length=50),
                ),
                ("description", models.TextField()),
                ("source_type", models.CharField(blank=True, db_index=True, max_length=50)),
                ("source_id", models.CharField(blank=True, db_index=True, max_length=100)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                (
                    "company",
                    models.ForeignKey(
                        db_index=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="enterprise_audit_logs",
                        to="organizations.organization",
                    ),
                ),
                (
                    "restaurant",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="enterprise_audit_logs",
                        to="organizations.restaurant",
                    ),
                ),
                (
                    "branch",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="enterprise_audit_logs",
                        to="organizations.branch",
                    ),
                ),
                (
                    "performed_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="enterprise_audit_logs",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Enterprise Audit Log",
                "verbose_name_plural": "Enterprise Audit Logs",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="enterpriseauditlog",
            index=models.Index(
                fields=["company", "action", "created_at"],
                name="enterprise_audit_co_action_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="enterpriseauditlog",
            index=models.Index(
                fields=["company", "restaurant", "action"],
                name="enterprise_audit_rest_action_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="enterpriseauditlog",
            index=models.Index(
                fields=["company", "restaurant", "branch", "action"],
                name="enterprise_audit_br_action_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="enterpriseauditlog",
            index=models.Index(
                fields=["performed_by", "created_at"],
                name="enterprise_audit_user_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="enterpriseauditlog",
            index=models.Index(
                fields=["source_type", "source_id"],
                name="enterprise_audit_source_idx",
            ),
        ),
    ]
